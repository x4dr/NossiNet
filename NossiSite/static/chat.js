$(document).ready(function(){
            var namespace = '/chat';

            var socket = io.connect('http://' + document.domain + ':' + location.port + namespace);

            // event handler for server sent data
            // the data is displayed in the "Received" section of the page
            socket.on('Message', function(msg) {
                var box = $('#chatbox');
                box.append('<br>' + $('<div/>').text(msg.data).html());
                box.scrollTop(box[0].scrollHeight);
            });

            socket.on('Status', function(msg) {
                document.getElementById('statusmessage').innerHTML = msg.status
            });

            socket.on('SetCmd', function(msg) {
                $('#message_data').val(msg.data)
            });

            socket.on('Exec', function(msg){
                eval(msg.command)

            });

            socket.on('connect', function() {
                socket.emit('ClientServerEvent', {data: '/connection established'});
            });
            var prevCommand = [];
            var commandCount = 0;
            var keyCount = 0;

            $('form#message').submit(function() {
                var message_data=$('#message_data').val();
                if(document.getElementById('message_data').value != ''){
                socket.emit('ClientServerEvent',
                        {data: message_data});
                commandCount++;
                keyCount = 0;
                prevCommand[commandCount] = message_data;
                document.getElementById('message_data').value = ''}
                return false;
            });

            $(document).keydown(function(event){
                var msgdata = $('#message_data');
                var index;
                msgdata.focus()
                if(event.which == 38){
                    keyCount++;
                    if(typeof prevCommand[keyCount] !== "undefined") {
                        index = prevCommand.length-keyCount;
                        msgdata.val(prevCommand[index]);
                    } else {
                        keyCount = 1;
                        index = prevCommand.length-keyCount;
                        msgdata.val(prevCommand[index]);
                    }
                    return false;
                }else if(event.which == 40) {
                    keyCount--;
                        if(typeof prevCommand[keyCount] !== "undefined") {
                        index = prevCommand.length-keyCount;
                        msgdata.val(prevCommand[index]);
                      //  moveCursorToEnd(msgdata)
                    } else {
                            keyCount = 0;
                        msgdata.val('');
                        }
                    return false;
                }
            });
        });