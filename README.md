# AI agent `rednote`
 AI agent for www.xiaohongshu.com thread

![](https://shields.io/badge/dependencies-Python_3.12-blue)
![](https://shields.io/badge/dependencies-Azure_OpenAI_Service-blue)


## Acknowledgement

[xhshow](https://github.com/Cloxl/xhshow) (modified)

## Install

Make sure you have a [rednote](https://www.xiaohongshu.com) social media account.

Create and activate a Python 3.12 virtual environment. Set the current directory to the program's root directory. Run the following command.

```
pip install -r requirements.txt
```

If you have [Chromium-based browsers](https://en.wikipedia.org/wiki/Chromium_(web_browser)#Browsers_based_on_Chromium), please install [J2TEAM cookies](https://chromewebstore.google.com/detail/j2team-cookies/okpidcojinmlaakglciglbpcpajaibco) extension. Otherwise, you need to find an alternative extension or manually copy any website's cookies from browser.

> [!NOTE]
>
> Function `auth.dump_cookies` is designed to load J2TEAM output files. If you use an alternative extension or manually paste the cookies, you need to modify this function, because pasted cookies table is in different format.
>
> The output table of `auth.dump_cookies` must have the following columns at least:
>
> - `name`
> - `value`
> - `expirationDate`  the expiry date of this cookies item
>
> Other columns are ignored.
>
> The output table must be saved in CSV format.

Get an OpenAI API key for a model which supports [function calling](https://platform.openai.com/docs/guides/function-calling?api-mode=chat), for example `gpt-4o`. This program calls `gpt-4o` by default if not customized.



## Usage

Run the following command.

```
python app.py
```

When the program hints that `rednote` cookies are expired: 

- Visit https://www.xiaohongshu.com/explore and log in your account.
- Visit https://as.xiaohongshu.com/ and export cookies by J2TEAMS extension (a file will be downloaded).
- Upload the file in this program's "Cookies" page.

*You can replace cookies (therefore can switch between `rednote` accounts) in "Cookies" page at the navigator. Existed conversations will not be affected by replacing cookies. Therefore, those conversations, which are created long time ago, cannot continue visiting data fetching tools as the cookies are expired.*

If AI agent is too radical to filter the user's message, adjust thresholds to "high" in [content filtering](https://learn.microsoft.com/en-us/azure/ai-foundry/concepts/content-filtering).
