import json
import logging

from openai import AzureOpenAI, BadRequestError

import get_data

with open("config.json") as f:
    config = json.load(f)
client = AzureOpenAI(
    azure_endpoint=config.get('azure_endpoint'),
    api_key=config.get('azure_api_key'),
    api_version=config.get('azure_api_version'),
)


class Conversation:
    def __init__(self, cookies: dict, max_func_call_rounds: int = 15):
        self.feed = get_data.Feed(cookies)
        self.detail = get_data.Detail(cookies)
        self.cookies = cookies
        self.searching_history = dict()
        self.busy = False
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_feed",
                    "description": "Retrieves recommended posts for the home page, personalized "
                                   "according to user preferences. Each call fetches the next "
                                   "batch of posts, simulating infinite scrolling behavior. "
                                   "Use this function to display or explore recommended content "
                                   "without specific search terms.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Searches posts by keyword or query terms. Each subsequent "
                                   "call retrieves additional matching results, mimicking "
                                   "infinite scrolling. Use this function when you want to find "
                                   "posts on specific topics or keywords.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query string for the search term.",
                            },
                        },
                        "required": ["query"],
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_detail",
                    "description": "Retrieves detailed content of a specific post, identified "
                                   "by `id` and `xsec_token`. Use this function to access "
                                   "complete post details necessary for answering detailed "
                                   "questions or further content analysis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "id_": {
                                "type": "string",
                                "description": "Unique identifier of the selected post.",
                            },
                            "xsec_token": {
                                "type": "string",
                                "description": "Access token for the selected post.",
                            },
                        },
                        "required": ["id_", "xsec_token"],
                    },
                }
            },
        ]
        role_prompt = """You are an AI agent integrated with three functions (get_feed, search, 
and get_detail) for interacting with a thread-based social media platform. Use these 
functions proactively and appropriately to answer user questions clearly, accurately, 
and efficiently.

Use get_feed to retrieve recommended posts based on user preferences. Multiple calls 
yield additional results.
Returns table of recommended posts with columns:
    id: Post unique identifier
    xsec_token: Token for accessing detailed content
    title: Post title
    cover_median_url: Medium-sized cover image URL
    user_id: Author's unique identifier (not useful)
    user_name: Author's nickname (not useful)
    user_xsec_token: Token for author's homepage (not useful)

Use search when a user requests posts about specific topics or keywords. Multiple calls 
yield additional results.
Returns table of matched posts with columns identical to get_feed.

Use get_detail to fetch comprehensive details for selected posts when detailed 
information is required for your responses.
Returns JSON dictionary containing:
    url: URL link of the post
    title: Title of the post
    description: Textual content of the post
    images: URLs of images attached to the post
    labels: Topic labels categorizing the post
    published_time: The time when the post is published
    location: The location of the author when publishing the post

Carefully decide which functions to invoke based on the user's intent, and provide 
objective and concise answers. Your answer should be based on information that exactly 
matches the function returns."""
        self.max_func_call_rounds = max_func_call_rounds
        self.messages = [
            {"role": "system", "content": role_prompt},
        ]
        self.title = None

    @staticmethod
    def _format_func_call_log(func_name: str, func_arg_dict: dict):
        func_arg_str = ", ".join(f"{k}=\"{v}\"" for k, v in func_arg_dict.items())
        return f"Function calling: {func_name}({func_arg_str})"

    def generate_title(self, user_message: str):
        summary_prompt = "Summarize the user's query into a title."
        messages = [
            {"role": "system", "content": summary_prompt},
            {"role": "user", "content": user_message}
        ]
        try:
            response = client.chat.completions.create(
                model=config.get('azure_deployment_name'),
                messages=messages,
                max_tokens=15,
                temperature=0,
                top_p=0.95,
            )
        except BadRequestError as e:
            logging.error(f"When summarizing the title, user message \"{user_message}\" "
                          f"is ignored. {e.body}")
            return e.body
        for choice in response.choices:
            title = choice.message.content
            if title is None:
                self.title = user_message[:20] + "..."
                for filter_name, filter_result in choice.content_filter_results.items():
                    if filter_result.get('filtered'):
                        logging.warning(
                            f"When summarizing the title, "
                            f"user message \"{user_message}\" is recognized to involve "
                            f"{filter_name}, {filter_result.get('severity')} severity."
                        )
            else:
                self.title = title.strip()
                break

    def answer_query(self, user_message: str):
        logging.info(f"User's message: {user_message}")
        self.messages.append(
            {"role": "user", "content": user_message},
        )
        n_func_call_rounds = 0
        while n_func_call_rounds < self.max_func_call_rounds:
            # API call: Ask the model to use the functions
            try:
                response = client.chat.completions.create(
                    model=config.get('azure_deployment_name'),
                    messages=self.messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
            except BadRequestError as e:
                logging.error(
                    f"When answering the user's query, user message \"{user_message}\" "
                    f"is ignored. {e.body}")
                return e.body
            # Process the model's response
            response_message = response.choices[0].message
            self.messages.append(response_message.__dict__)
            logging.info(f"Toolbox calling: {response_message}")

            # Handle function calls
            if response_message.tool_calls:
                n_func_call_rounds += 1
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    logging.info(self._format_func_call_log(function_name, function_args))

                    match function_name:
                        case "get_feed":
                            try:
                                posts = self.feed.get().to_json(orient='records')
                                function_response = json.dumps(posts)
                            except Exception as e:
                                function_response = json.dumps({"error": str(e)})
                        case "search":
                            query = function_args.get("query")
                            search_sess = self.searching_history.get(query)
                            if search_sess is None:
                                search_sess = get_data.Search(self.cookies, query)
                                self.searching_history[query] = search_sess
                            try:
                                posts = search_sess.get().to_json(orient='records')
                                function_response = json.dumps(posts)
                            except Exception as e:
                                function_response = json.dumps({"error": str(e)})
                        case "get_detail":
                            id_ = function_args.get("id_")
                            xsec_token = function_args.get("xsec_token")
                            try:
                                detail_json = self.detail.get(id_, xsec_token)
                                function_response = json.dumps(detail_json)
                            except Exception as e:
                                function_response = json.dumps({"error": str(e)})
                        case _:
                            function_response = json.dumps({"error": "Unknown function."})
                    self.messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
            else:
                break
