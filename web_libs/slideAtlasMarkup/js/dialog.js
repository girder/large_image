
(function () {
    "use strict";

    function Dialog(callback) {
        if ( ! SAM.DialogOverlay) {
            SAM.DialogOverlay = $('<div>')
                .appendTo('body')
                .css({
                    'position':'fixed',
                    'left':'0px',
                    'width': '100%',
                    'background-color':'#AAA',
                    'opacity':'0.4',
                    'z-index':'1010'})
                .saFullHeight()
                .hide();
        }

        this.Dialog =
            $('<div>')
            .appendTo('body')
            .css({'z-index':'1011'})
            .addClass("sa-view-dialog-div");

        this.Row1 = $('<div>')
            .addClass("sa-view-dialog-title")
            .appendTo(this.Dialog)
            .css({'width':'100%',
                  'height':'2.25em',
                  'box-sizing': 'border-box'});
        this.Title = $('<div>')
            .appendTo(this.Row1)
            .css({'float':'left'})
            .addClass("sa-view-dialog-title")
            .text("Title");
        this.CloseButton = $('<div>')
            .appendTo(this.Row1)
            .css({'float':'right'})
            .addClass("sa-view-dialog-close")
            .text("Close");

        this.Body =
            $('<div>')
            .appendTo(this.Dialog)
            .css({'width':'100%',
                  'box-sizing': 'border-box',
                  'margin-bottom':'30px'});

        this.ApplyButtonDiv = $('<div>')
            .appendTo(this.Dialog)
            .addClass("sa-view-dialog-apply-div");
        this.ApplyButton = $('<button>')
            .appendTo(this.ApplyButtonDiv)
            .addClass("sa-view-dialog-apply-button")
            .text("Apply");

        // Closure to pass a stupid parameter to the callback
        var self = this;
        (function () {
            // Return true needed to hide the spectrum color picker.
            self.CloseButton.click(function (e) {
                // hack
                SA.ContentEditableHasFocus = false;
                self.Hide();
                return true;
            });
            self.ApplyButton.click(function (e) {
                // hack
                SA.ContentEditableHasFocus = false;
                self.Hide(); 
                (callback)(); return true;
            });
        })();
    }

    Dialog.prototype.Show = function(modal) {
        // hack
        SA.ContentEditableHasFocus = true;
        var self = this;
        SAM.DialogOverlay.show();
        this.Dialog.fadeIn(300);

        if (modal) {
            SAM.DialogOverlay.off('click.dialog');
        } else {
            SAM.DialogOverlay.on(
                'click.dialog',
                function (e) { self.Hide(); });
        }
        SAM.ContentEditableHasFocus = true; // blocks viewer events.
    }

    Dialog.prototype.Hide = function () {
        SAM.DialogOverlay.off('click.dialog');
        SAM.DialogOverlay.hide();
        this.Dialog.fadeOut(300);
        SAM.ContentEditableHasFocus = false;
    }


    SAM.Dialog = Dialog;

})();
