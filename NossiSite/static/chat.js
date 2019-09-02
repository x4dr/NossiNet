$(document).ready(function(){
    var socket = io.connect('http://' + document.domain + ':' + location.port + '/chat');
    var charsocket = io.connect('http://' +  document.domain + ':' +location.port + '/character')
    var bell = new Audio("/static/bell.wav");
    var ring = false;
    var ringoverwrite = false;
    // event handler for server sent data
    // the data is displayed in the "Received" section of the page
    socket.on('Message', function(msg) {
        var box = $('#chatbox');
        box.append('<br>' + $('<div/>').text(msg.data).html());
        box.scrollTop(box[0].scrollHeight);
        if (ring){
            bell.play()
        }
    });

    charsocket.on('connect', function () {
        charsocket.emit('ClientServerEvent', {data: 'accessing character from chat'})
    });

    function keepAlive() {
        socket.emit('KeepAlive', {data:'blip'})
    }

    setInterval(keepAlive, 5000);

    function dotupdate(msg){
        var input = msg.data.split("§");
        var values = input[0].split("&");
        var maxima = input[1].split("&");
        var health = input[2].split("&")
        var Bloodpool= 0;
        var Bloodmax= 1;
        var Willpower= 0;
        var Willmax = 1;
        for (i = 0; i < values.length; i++){
            if (values[i].split("_")[0] == "Bloodpool"){
                Bloodpool = parseInt(values[i].split("_")[1]);
                Bloodmax = parseInt(maxima[i].split("_")[1])
            }else {
                Willpower = parseInt(values[i].split("_")[1]);
                Willmax = parseInt(maxima[i].split("_")[1])
            }
        }
        document.getElementById("bloodbar").style.width = (100*Bloodpool/Bloodmax).toString()+"%";
        document.getElementById("willbar").style.width = (100*Willpower/Willmax).toString()+"%";
        var Bash= parseInt(health[0]);
        var Lethal= parseInt(health[1]);
        var Aggravated= parseInt(health[2]);
        var Partial= parseInt(health[3]);
        Aggravated = Aggravated-0.2*Partial;
        health = 7-(Bash+Lethal+Aggravated);
        document.getElementById("healthbar").style.width = (100*health/7).toString()+"%";
        document.getElementById("healthbar").style.left = (100*(Bash+Lethal+Aggravated)/7).toString()+"%";
        document.getElementById("bashbar").style.width = (100*Bash/7).toString()+"%";
        document.getElementById("bashbar").style.left = (100*(Lethal+Aggravated)/7).toString()+"%";
        document.getElementById("lethalbar").style.width = (100*Lethal/7).toString()+"%";
        document.getElementById("lethalbar").style.left = (100*(Aggravated)/7).toString()+"%";
        document.getElementById("aggbar").style.width = (100*Aggravated/7).toString()+"%";
    }

    charsocket.on('DotUpdate', function (msg) {
        dotupdate(msg)
    });

    socket.on('DotUpdate', function (msg) {
        dotupdate(msg)
    } );

    $(window).blur(function(){
        ring=!ringoverwrite
    });
    $(window).focus(function(){
        ring=false
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
        $('#message_data').focus();
    });

    var prevCommand = [];
    var commandCount = 0;
    var keyCount = 0;

    $('form#message').submit(function() {
        var message_data=$('#message_data').val();
        if (message_data=="/ring off"){
            ringoverwrite = true
        }
        if (message_data=="/ring on"){
            ringoverwrite = false
        }
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
        if(event.which == 32){
            if (!msgdata.is(':focus')){
                msgdata.focus();
                return false
            }

        }


        if(event.which == 38){
            keyCount++;
            msgdata.focus();
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
            msgdata.focus();
            if(typeof prevCommand[keyCount] !== "undefined") {
                index = prevCommand.length-keyCount;
                msgdata.val(prevCommand[index]);
                //  moveCursorToEnd(msgdata)
            } else {
                if (prevCommand[commandCount] !== msgdata.val() && msgdata.val() !== '' ) {
                    commandCount++;
                    keyCount = 0;
                    prevCommand[commandCount] = msgdata.val();
                }
                msgdata.val('')
            }
            return false;
        }
    });
});