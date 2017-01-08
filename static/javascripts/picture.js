
$(document).ready(function() {
    //Croppic
    var cropperOptions = {
            cropUrl: '/croppic',
            // customUploadButtonId: 'uploadImgBtn',
            //modal: false,
            processInline: true,
            doubleZoomControls: false,
            rotateControls: true,
            loaderHtml: '<div class="loader bubblingG"><span id="bubblingG_1"></span><span id="bubblingG_2"></span><span id="bubblingG_3"></span></div>',
            onBeforeImgUpload: function() {},
            onAfterImgUpload: function() {},
            onImgDrag: function() {},
            onImgZoom: function() {},
            onBeforeImgCrop: function() {},
            onAfterImgCrop: function(response) {
                console.log("onAfterImgCrop response.filename :" + response.filename);
                $("#filename").val(response.filename);
                location.reload();
                //$("#myModal").modal();
            },
            onReset: function() {
            },
            onError: function(errormessage) {
                 console.log("onError errormessage :" + errormessage)
            }
        };
    var cropperHeader  = new Croppic('imgID', cropperOptions);

});

   function CroppicEvent() {
        $("#CroppicModal").modal();
    }

