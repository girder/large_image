//==============================================================================
// View Object
// Viewport (x_lowerleft, y_lowerleft, width, height)
// A view has its own camera and list of tiles to display.
// Views can share a cache for tiles.


(function () {
    "use strict";


    function View (parent, useWebGL) {
        this.Viewport = [0,0, 100,100];

        // Should widgets use shapes?
        // Should views be used independently to viewers?
        this.ShapeList = [];

        // connectome: remove Cache ivar.
        this.Camera = new SAM.Camera();
        this.OutlineColor = [0,0.5,0];
        this.OutlineMatrix = mat4.create();
        this.OutlineCamMatrix = mat4.create();

        this.CanvasDiv = parent;
        if ( parent) {
            this.CanvasDiv = parent;
        } else {
            this.CanvasDiv = $('<div>');
        }
        // 2d canvas
        // Add a new canvas.
        this.Canvas = $('<canvas>');

        if ( ! useWebGL) {
            this.Context2d = this.Canvas[0].getContext("2d");
        }

        this.Canvas
            .appendTo(this.CanvasDiv)
            .css({'position':'absolute',
                  'left'    : '0%',
                  'top'     : '0%',
                  'width'   :'100%',
                  'height'  :'100%'});

        this.CanvasDiv
            .addClass("sa-view-canvas-div");
    }

    // Try to remove all global and circular references to this view.
    View.prototype.Delete = function() {
        this.CanvasDiv.off('mousedown.viewer');
        this.CanvasDiv.off('mousemove.viewer');
        this.CanvasDiv.off('wheel.viewer');
        this.CanvasDiv.off('touchstart.viewer');
        this.CanvasDiv.off('touchmove.viewer');
        this.CanvasDiv.off('touchend.viewer');
        this.CanvasDiv.off('keydown.viewer');
        this.CanvasDiv.off('wheel.viewer');
        delete this.ShapeList;
        //delete this.Section;
        delete this.Camera;
        //delete this.Tiles;
        delete this.CanvasDiv;
        delete this.Canvas;
    }

    View.prototype.GetCamera = function() {
        return this.Camera;
    }


    // Get the current scale factor between pixels and world units.
    // World unit is the highest resolution image pixel.
    // Returns the size of a world pixel in screen pixels.
    // factor: screen/world
    // The default world pixel = 0.25e-6 meters
    View.prototype.GetPixelsPerUnit = function() {
        // Determine the scale difference between the two coordinate systems.
        var m = this.Camera.Matrix;

        // Convert from world coordinate to view (-1->1);
        return 0.5*this.Viewport[2] / (m[3] + m[15]); // m[3] for x, m[7] for height
    }

    View.prototype.GetMetersPerUnit = function() {
        var cache = this.GetCache();
        var dist;
        if ( ! cache) {
            dist = {value : 250,
                    units : 'nm'};
        } else {
            dist = {value : cache.Image.spacing[0],
                    units : cache.Image.units};
        }
        SAM.ConvertToMeters(dist);
        return dist.value;
    }

    // TODO: Get rid of these since the user can manipulate the parent / canvas
    // div which can be passed into the constructor.
    View.prototype.appendTo = function(j) {
        return this.CanvasDiv.appendTo(j);
    }

    View.prototype.remove = function(j) {
        return this.CanvasDiv.remove(j);
    }

    View.prototype.css = function(j) {
        return this.CanvasDiv.css(j);
    }

    // TODO: Get rid of this.
    View.prototype.GetViewport = function() {
        return this.Viewport;
    }

    View.prototype.GetWidth = function() {
        return this.CanvasDiv.width();
    }

    View.prototype.GetHeight = function() {
        return this.CanvasDiv.height();
    }

    // The canvasDiv changes size, the width and height of the canvas and
    // camera need to follow.  I am going to make this the resize callback.
    View.prototype.UpdateCanvasSize = function() {
        if ( ! this.CanvasDiv.is(':visible') ) {
            return;
        }

        var pos = this.CanvasDiv.position();
        //var width = this.CanvasDiv.innerWidth();
        //var height = this.CanvasDiv.innerHeight();
        var width = this.CanvasDiv.width();
        var height = this.CanvasDiv.height();
        // resizable is making width 0 intermitently ????
        if (width <= 0 || height <= 0) { return false; }

        this.SetViewport([pos.left, pos.top, width, height]);

        return true;
    }


    // This is meant to be called internally by UpdateCanvasSize.
    // However, if the parent(canvasDiv) is hidden, it might need to be
    // set explcitly.
    // TODO: Change this to simply width and height.
    View.prototype.SetViewport = function(viewport) {
        var width = viewport[2];
        var height = viewport[3];

        this.Canvas.attr("width", width.toString());
        this.Canvas.attr("height", height.toString());

        // TODO: Get rid of this ivar
        this.Viewport = viewport;

        // TODO: Just set the width and height of the camera.
        // There is no reason, the camera needs to know the
        // the position of the cameraDiv.
        this.Camera.SetViewport(viewport);
    }


    View.prototype.CaptureImage = function() {
        var url = this.Canvas[0].toDataURL();
        var newImg = document.createElement("img"); //create
        newImg.src = url;
        return newImg;
    }


    // Legacy
    // A list of shapes to render in the view
    View.prototype.AddShape = function(shape) {
        this.ShapeList.push(shape);
    }

    // NOTE: AnnotationLayer has the api where the shapes draw themselves (with
    // reference to this view.  I like that better than the view knowing
    // how to draw all these things.
    View.prototype.DrawShapes = function () {
        if ( ! this.CanvasDiv.is(':visible') ) {
            return;
        }
        for(var i=0; i<this.ShapeList.length; i++){
            this.ShapeList[i].Draw(this);
        }
    }

    View.prototype.Clear = function () {
        this.Context2d.setTransform(1, 0, 0, 1, 0, 0);
        // TODO: get width and height from the canvas.
        this.Context2d.clearRect(0,0,this.Viewport[2],this.Viewport[3]);
    }


    View.prototype.DrawHistory = function (windowHeight) {
        if ( this.gl) {
            alert("Drawing history does not work with webGl yet.");
        } else {
            var ctx = this.Context2d;
            ctx.save();
            ctx.setTransform(1, 0, 0, 1, 0, 0);

            // Start with a transform that flips the y axis.
            ctx.setTransform(1, 0, 0, -1, 0, this.Viewport[3]);

            // Map (-1->1, -1->1) to the viewport.
            // Origin of the viewport does not matter because drawing is relative
            // to this view's canvas.
            ctx.transform(0.5*this.Viewport[2], 0.0,
                          0.0, 0.5*this.Viewport[3],
                          0.5*this.Viewport[2],
                          0.5*this.Viewport[3]);

            //ctx.fillRect(0.0,0.1,0.5,0.5); // left, right, width, height

            // The camera maps the world coordinate system to (-1->1, -1->1).
            var cam = this.Camera;
            var aspectRatio = cam.ViewportWidth / cam.ViewportHeight;

            var h = 1.0 / cam.Matrix[15];
            ctx.transform(cam.Matrix[0]*h, cam.Matrix[1]*h,
                          cam.Matrix[4]*h, cam.Matrix[5]*h,
                          cam.Matrix[12]*h, cam.Matrix[13]*h);

            for (var i = 0; i < TIME_LINE.length; ++i) {
                var cam = TIME_LINE[i].ViewerRecords[0].Camera;
                var height = cam.GetHeight();
                var width = cam.GetWidth();
                // camer roll is already in radians.
                var c = Math.cos(cam.Roll);
                var s = Math.sin(cam.Roll);
                ctx.save();
                // transform to put focal point at 0,0
                ctx.transform(c, -s,
                              s, c,
                              cam.FocalPoint[0], cam.FocalPoint[1]);

                // Compute the zoom factor for opacity.
                var opacity = 2* windowHeight / height;
                if (opacity > 1.0) { opacity = 1.0; }

                ctx.fillStyle = "rgba(0,128,0," + opacity + ")";
                ctx.fillRect(-width/2, -height/2, width, height); // left, right, width, height
                ctx.stroke();
                ctx.restore();
            }
            ctx.restore();
        }
    }

    // Draw a cross hair in the center of the view.
    View.prototype.DrawFocalPoint = function () {
        if ( this.gl) {
            alert("Drawing focal point does not work with webGl yet.");
        } else {
            var x = this.Viewport[2] * 0.5;
            var y = this.Viewport[3] * 0.5;
            var ctx = this.Context2d;
            ctx.save();
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.strokeStyle = "rgba(255,255,200,100)";
            ctx.fillStyle = "rgba(0,0,50,100)";

            ctx.beginPath();
            ctx.fillRect(x-30,y-1,60,3);
            ctx.rect(x-30,y-1,60,3);
            ctx.fillRect(x-1,y-30,3,60);
            ctx.rect(x-1,y-30,3,60);

            var r = y / 2;
            ctx.beginPath();
            ctx.moveTo(x-r,y-r+30);
            ctx.lineTo(x-r,y-r);
            ctx.lineTo(x-r+30,y-r);
            ctx.moveTo(x+r,y-r+30);
            ctx.lineTo(x+r,y-r);
            ctx.lineTo(x+r-30,y-r);
            ctx.moveTo(x+r,y+r-30);
            ctx.lineTo(x+r,y+r);
            ctx.lineTo(x+r-30,y+r);
            ctx.moveTo(x-r,y+r-30);
            ctx.lineTo(x-r,y+r);
            ctx.lineTo(x-r+30,y+r);
            ctx.stroke();

            ++r;
            ctx.beginPath();
            ctx.strokeStyle = "rgba(0,0,50,100)";
            ctx.moveTo(x-r,y-r+30);
            ctx.lineTo(x-r,y-r);
            ctx.lineTo(x-r+30,y-r);
            ctx.moveTo(x+r,y-r+30);
            ctx.lineTo(x+r,y-r);
            ctx.lineTo(x+r-30,y-r);
            ctx.moveTo(x+r,y+r-30);
            ctx.lineTo(x+r,y+r);
            ctx.lineTo(x+r-30,y+r);
            ctx.moveTo(x-r,y+r-30);
            ctx.lineTo(x-r,y+r);
            ctx.lineTo(x-r+30,y+r);
            ctx.stroke();
            ctx.restore();
        }
    }

    // Draw a cross hair at each correlation point.
    // pointIdx is 0 or 1.  It indicates which correlation point should be drawn.
    View.prototype.DrawCorrelations = function (correlations, pointIdx) {
        if ( this.gl) {
            alert("Drawing correlations does not work with webGl yet.");
        } else {
            var ctx = this.Context2d;
            ctx.save();
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.strokeStyle = "rgba(200,255,255,100)";
            ctx.fillStyle = "rgba(255,0,0,100)";
            for (var i = 0; i < correlations.length; ++i) {
                var wPt = correlations[i].GetPoint(pointIdx);
                var m = this.Camera.Matrix;
                // Change coordinate system from world to -1->1
                var x = (wPt[0]*m[0] + wPt[1]*m[4]
                         + m[12]) / m[15];
                var y = (wPt[0]*m[1] + wPt[1]*m[5]
                         + m[13]) / m[15];
                // Transform coordinate system from -1->1 to canvas
                x = (1.0 + x) * this.Viewport[2] * 0.5;
                y = (1.0 - y) * this.Viewport[3] * 0.5;

                ctx.beginPath();
                ctx.fillRect(x-20,y-1,40,3);
                ctx.rect(x-20,y-1,40,3);
                ctx.fillRect(x-1,y-20,3,40);
                ctx.rect(x-1,y-20,3,40);

                ctx.stroke();
            }
            ctx.restore();
        }
    }

    // NOTE: Not used anymore. Viewer uses a DOM.
    View.prototype.DrawCopyright = function (copyright) {
        if (copyright == undefined || MASK_HACK) {
            return;
        }
        if ( this.gl) {
            // not implemented yet.
        } else {
            this.Context2d.setTransform(1, 0, 0, 1, 0, 0);
            this.Context2d.font = "18px Arial";
            var x = this.Viewport[2]*0.5 - 50;
            var y = this.Viewport[3]-10;
            this.Context2d.fillStyle = "rgba(128,128,128,0.5)";
            this.Context2d.fillText(copyright,x,y);
            //this.Context2d.strokeStyle = "rgba(255,255,255,0.5)";
            //this.Context2d.strokeText(copyright,x,y);
        }
    }

    // I think this was only used for webgl.  Not used anymore
    View.prototype.DrawOutline = function(backgroundFlag) {
        if (this.gl) {
            var program = polyProgram;
            this.gl.useProgram(program);

            this.gl.viewport(this.Viewport[0],
                             this.Viewport[3]-this.Viewport[1],
                             this.Viewport[2],
                             this.Viewport[3]);

            // Draw a line around the viewport, so move (0,0),(1,1) to (-1,-1),(1,1)
            mat4.identity(this.OutlineCamMatrix);
            this.OutlineCamMatrix[0] = 2.0; // width x
            this.OutlineCamMatrix[5] = 2.0; // width y
            this.OutlineCamMatrix[10] = 0;
            this.OutlineCamMatrix[12] = -1.0;
            this.OutlineCamMatrix[13] = -1.0;
            var viewFrontZ = this.Camera.ZRange[0]+0.001;
            var viewBackZ = this.Camera.ZRange[1]-0.001;
            this.OutlineCamMatrix[14] = viewFrontZ; // front plane

            mat4.identity(this.OutlineMatrix);

            this.gl.uniformMatrix4fv(program.mvMatrixUniform, false, this.OutlineMatrix);

            if (backgroundFlag) {
                // White background fill
                this.OutlineCamMatrix[14] = viewBackZ; // back plane
                this.gl.uniformMatrix4fv(program.pMatrixUniform, false, this.OutlineCamMatrix);
                this.gl.uniform3f(program.colorUniform, 1.0, 1.0, 1.0);
                this.gl.bindBuffer(this.gl.ARRAY_BUFFER, squarePositionBuffer);
                this.gl.vertexAttribPointer(program.vertexPositionAttribute,
                                            squarePositionBuffer.itemSize,
                                            this.gl.FLOAT, false, 0, 0);
                this.gl.drawArrays(this.gl.TRIANGLE_STRIP, 0, squarePositionBuffer.numItems);
            }

            // outline
            this.OutlineCamMatrix[14] = viewFrontZ; // force in front
            this.gl.uniformMatrix4fv(program.pMatrixUniform, false, this.OutlineCamMatrix);
            this.gl.uniform3f(program.colorUniform, this.OutlineColor[0], this.OutlineColor[1], this.OutlineColor[2]);
            this.gl.bindBuffer(this.gl.ARRAY_BUFFER, squareOutlinePositionBuffer);
            this.gl.vertexAttribPointer(program.vertexPositionAttribute,
                                        squareOutlinePositionBuffer.itemSize,
                                        this.gl.FLOAT, false, 0, 0);
            this.gl.drawArrays(this.gl.LINE_STRIP, 0, squareOutlinePositionBuffer.numItems);
        }
    }


    SAM.View = View;

})();
