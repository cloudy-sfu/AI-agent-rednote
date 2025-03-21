// const conv_list = document.getElementById('articles-list');
const msg_list = document.getElementById('messages-list');
const user_message_box = document.getElementById('user-message');

// function change_title(conv_id, new_title) {
//     const conv_item = conv_list.querySelector(`li[conv_id="${conv_id}"]`);
//     conv_item.firstElementChild.text = new_title;
// }

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
            append_message_list(`<p class="text-danger">${response}</p>`)
        }
    });
}


$('#conv-send').submit(function(event) {
    event.preventDefault();
    user_message_box.readOnly = true;
    const form = $(this);
    const action_target = form.attr('action'); // Get the form's action URL
    $.ajax({
        type: 'POST',
        url: action_target,
        data: form.serialize(), // Serialize the form data
        success: function(response) {
            user_message_box.readOnly = false;
            user_message_box.value = '';
            if (response['error']) {
                for (let error_message of response['error']) {
                    append_message_list(`<p class="text-danger">${error_message}</p>`)
                }
            }
        },
        error: function() {
            user_message_box.readOnly = false;
            append_message_list(`<p class="text-danger">Fail to get response from the AI agent, please try again.</p>`);
        }
    });
    update_messages(form[0].conv_id.value);
});