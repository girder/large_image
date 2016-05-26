
//==============================================================================
// Feedback for the image that will be downloaded with the cutout service.
// Todo:
// - Key events and tooltips for buttons.
//   This is difficult because the widget would have to be active all the time.
//   Hold off on this.


(function () {
    "use strict";

    function CutoutWidget (parent, viewer) {
        this.Viewer = viewer;
        this.Layer = viewer.AnnotationLayer;
        var cam = layer.GetCamera();
        var fp = cam.GetFocalPoint();

        var rad = cam.Height / 4;
        this.Bounds = [fp[0]-rad,fp[0]+rad, fp[1]-rad,fp[1]+rad];
        this.DragBounds = [fp[0]-rad,fp[0]+rad, fp[1]-rad,fp[1]+rad];

        layer.AddWidget(this);
        eventuallyRender();

        // Bits that indicate which edges are active.
        this.Active = 0;

        var self = this;
        this.Div = $('<div>')
            .appendTo(parent)
            .addClass("sa-view-cutout-div");
        $('<button>')
            .appendTo(this.Div)
            .text("Cancel")
            .addClass("sa-view-cutout-button")
            .click(function(){self.Cancel();});
        $('<button>')
            .appendTo(this.Div)
            .text("Download")
            .addClass("sa-view-cutout-button")
            .click(function(){self.Accept();});

        this.Select = $('<select>')
            .appendTo(this.Div);
        $('<option>').appendTo(this.Select)
            .attr('value', 0)
            .text("tif");
        $('<option>').appendTo(this.Select)
            .attr('value', 1)
            .text("jpeg");
        $('<option>').appendTo(this.Select)
            .attr('value', 2)
            .text("png");
        $('<option>').appendTo(this.Select)
            .attr('value', 3)
            .text("svs");

        this.Label = $('<div>')
            .addClass("sa-view-cutout-label")
            .appendTo(this.Div);
        this.UpdateBounds();
        this.HandleMouseUp();
    }

    CutoutWidget.prototype.Accept = function () {
        this.Deactivate();
        var types = ["tif", "jpeg", "png", "svs"]
        var image_source = this.Viewer.GetCache().Image;
        // var bounds = [];
        // for (var i=0; i <this.Bounds.length; i++) {
        //  bounds[i] = this.Bounds[i] -1;
        // }

        window.location = "/cutout/" + image_source.database + "/" +
            image_source._id + "/image."+types[this.Select.val()]+"?bounds=" + JSON.stringify(this.Bounds);
    }


    CutoutWidget.prototype.Cancel = function () {
        this.Deactivate();
    }

    CutoutWidget.prototype.Serialize = function() {
        return false;
    }

    CutoutWidget.prototype.Draw = function(view) {
        var center = [(this.DragBounds[0]+this.DragBounds[1])*0.5,
                      (this.DragBounds[2]+this.DragBounds[3])*0.5];
        var cam = view.Camera;
        var viewport = view.Viewport;

        if (view.gl) {
            alert("webGL cutout not supported");
        } else {
            // The 2d canvas was left in world coordinates.
            var ctx = view.Context2d;
            var cam = view.Camera;
            ctx.save();
            ctx.setTransform(1,0,0,1,0,0);
            this.DrawRectangle(ctx, this.Bounds, cam, "#00A", 1, 0);
            this.DrawRectangle(ctx, this.DragBounds, cam, "#000",2, this.Active);
            this.DrawCenter(ctx, center, cam, "#000");
            ctx.restore();
        }
    }

    CutoutWidget.prototype.DrawRectangle = function(ctx, bds, cam, color,
                                                    lineWidth, active) {
        // Convert the for corners to view.
        var pt0 = cam.ConvertPointWorldToViewer(bds[0],bds[2]);
        var pt1 = cam.ConvertPointWorldToViewer(bds[1],bds[2]);
        var pt2 = cam.ConvertPointWorldToViewer(bds[1],bds[3]);
        var pt3 = cam.ConvertPointWorldToViewer(bds[0],bds[3]);

        ctx.lineWidth = lineWidth;

        ctx.beginPath();
        ctx.strokeStyle=(active&4)?"#FF0":color;
        ctx.moveTo(pt0[0], pt0[1]);
        ctx.lineTo(pt1[0], pt1[1]);
        ctx.stroke();

        ctx.beginPath();
        ctx.strokeStyle=(active&2)?"#FF0":color;
        ctx.moveTo(pt1[0], pt1[1]);
        ctx.lineTo(pt2[0], pt2[1]);
        ctx.stroke();

        ctx.beginPath();
        ctx.strokeStyle=(active&8)?"#FF0":color;
        ctx.moveTo(pt2[0], pt2[1]);
        ctx.lineTo(pt3[0], pt3[1]);
        ctx.stroke();

        ctx.beginPath();
        ctx.strokeStyle=(active&1)?"#FF0":color;
        ctx.moveTo(pt3[0], pt3[1]);
        ctx.lineTo(pt0[0], pt0[1]);
        ctx.stroke();
    }

    CutoutWidget.prototype.DrawCenter = function(ctx, pt, cam, color) {
        // Convert the for corners to view.
        var pt0 = cam.ConvertPointWorldToViewer(pt[0],pt[1]);

        ctx.strokeStyle=(this.Active&16)?"#FF0":color;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(pt0[0]-5, pt0[1]);
        ctx.lineTo(pt0[0]+5, pt0[1]);
        ctx.moveTo(pt0[0], pt0[1]-5);
        ctx.lineTo(pt0[0], pt0[1]+5);
        ctx.stroke();
    }


    CutoutWidget.prototype.HandleKeyPress = function(keyCode, shift) {
        // Return is the same as except.
        if (event.keyCode == 67) {
            alert("Accept");
        }
        // esc or delete: cancel
        if (event.keyCode == 67) {
            alert("Cancel");
        }

        return true;
    }

    CutoutWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    }

    CutoutWidget.prototype.HandleMouseDown = function(event) {
        if (event.which != 1) {
            return false;
        }
        return true;
    }

    // returns false when it is finished doing its work.
    CutoutWidget.prototype.HandleMouseUp = function() {
        if (this.Bounds[0] > this.Bounds[1]) {
            var tmp = this.Bounds[0];
            this.Bounds[0] = this.Bounds[1];
            this.Bounds[1] = tmp;
        }
        if (this.Bounds[2] > this.Bounds[3]) {
            var tmp = this.Bounds[2];
            this.Bounds[2] = this.Bounds[3];
            this.Bounds[3] = tmp;
        }

        this.DragBounds = this.Bounds.slice(0);
        eventuallyRender();
    }

    CutoutWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;

        if (event.which == 0) {
            this.CheckActive(event);
            return;
        }

        if (this.Active) {
            var cam = this.Layer.GetCamera();
            var pt = cam.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
            if (this.Active&1) {
                this.DragBounds[0] = pt[0];
            }
            if (this.Active&2) {
                this.DragBounds[1] = pt[0];
            }
            if (this.Active&4) {
                this.DragBounds[2] = pt[1];
            }
            if (this.Active&8) {
                this.DragBounds[3] = pt[1];
            }
            if (this.Active&16) {
                var dx = pt[0] - 0.5*(this.DragBounds[0]+this.DragBounds[1]);
                var dy = pt[1] - 0.5*(this.DragBounds[2]+this.DragBounds[3]);
                this.DragBounds[0] += dx;
                this.DragBounds[1] += dx;
                this.DragBounds[2] += dy;
                this.DragBounds[3] += dy;
            }
            this.UpdateBounds();
            eventuallyRender();
            return true;
        }
        return false;
    }

    // Bounds follow drag bounds, but snap to the tile grid.
    // Maybe we should not force Bounds to contain DragBounds.
    // Bounds Grow when dragging the center. Maybe
    // round rather the use floor and ceil.
    CutoutWidget.prototype.UpdateBounds = function(event) {
        var cache = this.Viewer.GetCache();
        var tileSize = cache.Image.TileSize;
        //this.Bounds[0] = Math.floor(this.DragBounds[0]/tileSize) * tileSize;
        //this.Bounds[1] =  Math.ceil(this.DragBounds[1]/tileSize) * tileSize;
        //this.Bounds[2] = Math.floor(this.DragBounds[2]/tileSize) * tileSize;
        //this.Bounds[3] =  Math.ceil(this.DragBounds[3]/tileSize) * tileSize;
        var bds = [0,0,0,0];
        bds[0] = Math.round(this.DragBounds[0]/tileSize) * tileSize;
        bds[1] = Math.round(this.DragBounds[1]/tileSize) * tileSize;
        bds[2] = Math.round(this.DragBounds[2]/tileSize) * tileSize;
        bds[3] = Math.round(this.DragBounds[3]/tileSize) * tileSize;

        // Keep the bounds in the image.
        // min and max could be inverted.
        // I am not sure the image bounds have to be on the tile boundaries.
        var imgBds = cache.Image.bounds;
        if (bds[0] < imgBds[0]) bds[0] = imgBds[0];
        if (bds[1] < imgBds[0]) bds[1] = imgBds[0];
        if (bds[2] < imgBds[2]) bds[2] = imgBds[2];
        if (bds[3] < imgBds[2]) bds[3] = imgBds[2];

        if (bds[0] > imgBds[1]) bds[0] = imgBds[1];
        if (bds[1] > imgBds[1]) bds[1] = imgBds[1];
        if (bds[2] > imgBds[3]) bds[2] = imgBds[3];
        if (bds[3] > imgBds[3]) bds[3] = imgBds[3];

        // Do not the bounds go to zero area.
        if (bds[0] != bds[1]) {
            this.Bounds[0] = bds[0];
            this.Bounds[1] = bds[1];
        }
        if (bds[2] != bds[3]) {
            this.Bounds[2] = bds[2];
            this.Bounds[3] = bds[3];
        }

        // Update the label.
        var dim = [this.Bounds[1]-this.Bounds[0],this.Bounds[3]-this.Bounds[2]];
        this.Label.text(dim[0] + " x " + dim[1] +
                        " = " + this.FormatPixels(dim[0]*dim[1]) + "pixels");
    }

    CutoutWidget.prototype.FormatPixels = function(num) {
        if (num > 1000000000) {
            return Math.round(num/1000000000) + "G";
        }
        if (num > 1000000) {
            return Math.round(num/1000000) + "M";
        }
        if (num > 1000) {
            return Math.round(num/1000) + "k";
        }
        return num;
    }


    CutoutWidget.prototype.HandleTouchPan = function(event) {
    }

    CutoutWidget.prototype.HandleTouchPinch = function(event) {
    }

    CutoutWidget.prototype.HandleTouchEnd = function(event) {
    }


    CutoutWidget.prototype.CheckActive = function(event) {
        var cam = this.Layer.GetCamera();
        // it is easier to make the comparison in slide coordinates,
        // but we need a tolerance in pixels.
        var tolerance = cam.Height / 200;
        var pt = cam.ConvertPointViewerToWorld(event.offsetX, event.offsetY);
        var active = 0;

        var inX = (this.DragBounds[0]-tolerance < pt[0] && pt[0] < this.DragBounds[1]+tolerance);
        var inY = (this.DragBounds[2]-tolerance < pt[1] && pt[1] < this.DragBounds[3]+tolerance);
        if (inY && Math.abs(pt[0]-this.DragBounds[0]) < tolerance) {
            active = active | 1;
        }
        if (inY && Math.abs(pt[0]-this.DragBounds[1]) < tolerance) {
            active = active | 2;
        }
        if (inX && Math.abs(pt[1]-this.DragBounds[2]) < tolerance) {
            active = active | 4;
        }
        if (inX && Math.abs(pt[1]-this.DragBounds[3]) < tolerance) {
            active = active | 8;
        }

        var center = [(this.DragBounds[0]+this.DragBounds[1])*0.5, 
                      (this.DragBounds[2]+this.DragBounds[3])*0.5];
        tolerance *= 2;
        if (Math.abs(pt[0]-center[0]) < tolerance &&
            Math.abs(pt[1]-center[1]) < tolerance) {
            active = active | 16;
        }

        if (active != this.Active) {
            this.SetActive(active);
            eventuallyRender();
        }

        return false;
    }

    // Multiple active states. Active state is a bit confusing.
    CutoutWidget.prototype.GetActive = function() {
        return this.Active;
    }

    CutoutWidget.prototype.Deactivate = function() {
        this.Div.remove();
        if (this.Layer == null) {
            return;
        }
        this.Layer.DeactivateWidget(this);
        this.Layer.RemoveWidget(this);

        eventuallyRender();
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    CutoutWidget.prototype.SetActive = function(active) {
        if (this.Active == active) {
            return;
        }
        this.Active = active;

        if ( active != 0) {
            this.Layer.ActivateWidget(this);
        } else {
            this.Layer.DeactivateWidget(this);
        }
        eventuallyRender();
    }

    SAM.CutoutWidget = CutoutWidget;

})();




