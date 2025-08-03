const msg_list = document.getElementById('messages-list');

function append_message_list(messages_html) {
    msg_list.innerHTML += messages_html;
}

function get_start_id() {
    const messages = msg_list.querySelectorAll(`div[message_id]`);
    let start_id = 0;
    messages.forEach(div => {
        const message_id = parseInt(div.getAttribute('message_id'));
        if (!isNaN(message_id)) {
            const start_id_0 = message_id + 1;
            if (start_id_0 > start_id) start_id = start_id_0;
        }
    });
    return start_id;
}

function update_messages(conv_id) {
    $.ajax({
        type: 'POST',
        url: "/conv/update",
        data: {conv_id: conv_id, start_id: get_start_id()},
        success: function(response) {
            if (response['error']) {
                append_message_list(`<p class="text-danger">${response['error']}</p>`);
            } else if (response['messages']) {
                append_message_list(response['messages']);
            }
            if (response['busy']) {
                setTimeout(update_messages, 1000, conv_id);
            }
        },
        error: function(response) {
            append_message_list(`<p class="text-danger">Cannot update messages. HTTP status ${response.status}</p>`)
        }
    });
}

async function add_conversation() {
    try {
        const response = await fetch("/conv/add");
        if (!response.ok) {
            append_message_list(`<p class="text-danger">Cannot create new conversation. HTTP status ${response.status}</p>`);
            return
        } else if (response.redirected) {
            location.href = response.url;  // Redirected to cookies page.
            return
        }
        return await response.json();
    } catch (error) {
        append_message_list(`<p class="text-danger">Cannot create new conversation. ${error}</p>`);
    }
}

async function add_conversation_ui() {
    const response_json = await add_conversation();
    const conv_id = parseInt(response_json['conv_id']);
    if (isNaN(conv_id)) {
        append_message_list(`<p class="text-danger">Cannot to create new conversation. <code>conv_id=${conv_id}</code></p>`)
        return
    }
    location.href = `/conv/${conv_id}`;
}

$('#conv-send').submit(async function(event) {
    event.preventDefault();
    user_message.readOnly = true;
    const form = $(this);
    const action_target = form.attr('action'); // Get the form's action URL
    if (!form[0].conv_id.value) {
        const response_json = await add_conversation();
        const conv_id = parseInt(response_json['conv_id']);
        if (isNaN(conv_id)) {
            return
        }
        form[0].conv_id.value = conv_id;
    }

    $.ajax({
        type: 'POST',
        url: action_target,
        data: form.serialize(), // Serialize the form data
        success: function(response) {
            user_message.readOnly = false;
            user_message.value = '';
            if (response['error']) {
                for (let error_message of response['error']) {
                    append_message_list(`<p class="text-danger">${error_message}</p>`)
                }
            }
        },
        error: function() {
            user_message.readOnly = false;
            append_message_list(`<p class="text-danger">Fail to get response from the AI agent, please try again.</p>`);
        }
    });
    update_messages(form[0].conv_id.value);
});