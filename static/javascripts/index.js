$(function () {
    var $messages = $('.messages-content'), i = 0;

    $(window).load(function() {
      $messages.mCustomScrollbar();

    });


    namespace = '';
    var socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace);

    socket.on('connect', function () {
        //console.log('connected!');
        socket.emit('join', {room: 'A_Room'});
    });

    function updateScrollbar() {
      $messages.mCustomScrollbar("update").mCustomScrollbar('scrollTo', 'bottom', {
        scrollInertia: 10,
        timeout: 0
      });
    }

    function setDate(time){
      $('<div class="timestamp">' + time + '</div>').appendTo($('.message:last'));
    }

    function insertMessage() {
      //console.log('insertMessage');
      msg = $('.message-input').val();
      if ($.trim(msg) == '') {
        return false;
      }
      //console.log('send Inqueiry');
      var obj = {
          msg: msg,
          room: 'A_Room'
      };
      socket.emit('sendInquiry', obj);
    }


    socket.on('getInquiry', function (msg) {
          //console.log(msg.msg);
          $('<div class="message new"><figure class="avatar"><img src="/static/mugshot/'+msg.PictureUrl+'" /></figure>' + msg.msg + '</div>').appendTo($('.mCSB_container')).addClass('new');
          setDate(msg.time);
          $('.message-input').val(null);
          updateScrollbar();
    });


    $('.message-submit').click(function() {
      insertMessage();
    });

    $(window).on('keydown', function(e) {
      if (e.which == 13) {
        insertMessage();
        return false;
      }
    });


    function fakeMessage() {
      if ($('.message-input').val() != '') {
        return false;
      }
      $('<div class="message loading new"><figure class="avatar"><img src="http://s3-us-west-2.amazonaws.com/s.cdpn.io/156381/profile/profile-80_4.jpg" /></figure><span></span></div>').appendTo($('.mCSB_container'));
      updateScrollbar();

      setTimeout(function() {
        $('.message.loading').remove();
        $('<div class="message new"><figure class="avatar"><img src="http://s3-us-west-2.amazonaws.com/s.cdpn.io/156381/profile/profile-80_4.jpg" /></figure>' + Fake[i] + '</div>').appendTo($('.mCSB_container')).addClass('new');
        setDate();
        updateScrollbar();
        i++;
      }, 1000 + (Math.random() * 20) * 100);

    }


});