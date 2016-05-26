
(function () {
    "use strict";

    function Circle() {
        SAM.Shape.call(this);
        this.Radius = 10; // Radius in pixels
        this.Origin = [10000,10000]; // Center in world coordinates.
        this.OutlineColor = [0,0,0];
        this.PointBuffer = [];
    };
    Circle.prototype = new SAM.Shape;


    // I know javascript does not have desctuctors.
    // I was thinking of calling this explicilty to hasten freeing of resources.
    Circle.prototype.destructor=function() {
        // Get rid of the buffers?
    }

    Circle.prototype.UpdateBuffers = function(view) {
        this.PointBuffer = [];
        var cellData = [];
        var lineCellData = [];
        var numEdges = Math.floor(this.Radius/2)+10;
        // NOTE: numEdges logic will not work in world coordinates.
        // Limit numEdges to 180 to mitigate this issue.
        if (numEdges > 50 || ! this.FixedSize ) {
            numEdges = 50;
        }

        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);

        if  (view.gl) {
            if (this.LineWidth == 0) {
                for (var i = 0; i <= numEdges; ++i) {
                    var theta = i*2*3.14159265359/numEdges;
                    this.PointBuffer.push(this.Radius*Math.cos(theta));
                    this.PointBuffer.push(this.Radius*Math.sin(theta));
                    this.PointBuffer.push(0.0);
                }

                // Now create the triangles
                // It would be nice to have a center point,
                // but this would mess up the outline.
                for (var i = 2; i < numEdges; ++i) {
                    cellData.push(0);
                    cellData.push(i-1);
                    cellData.push(i);
                }

                this.VertexPositionBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ARRAY_BUFFER, this.VertexPositionBuffer);
                view.gl.bufferData(view.gl.ARRAY_BUFFER, new Float32Array(this.PointBuffer), view.gl.STATIC_DRAW);
                this.VertexPositionBuffer.itemSize = 3;
                this.VertexPositionBuffer.numItems = this.PointBuffer.length / 3;

                this.CellBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ELEMENT_ARRAY_BUFFER, this.CellBuffer);
                view.gl.bufferData(view.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(cellData), view.gl.STATIC_DRAW);
                this.CellBuffer.itemSize = 1;
                this.CellBuffer.numItems = cellData.length;
            } else {
                //var minRad = this.Radius - (this.LineWidth/2.0);
                //var maxRad = this.Radius + (this.LineWidth/2.0);
                var minRad = this.Radius;
                var maxRad = this.Radius + this.LineWidth;
                for (var i = 0; i <= numEdges; ++i) {
                    var theta = i*2*3.14159265359/numEdges;
                    this.PointBuffer.push(minRad*Math.cos(theta));
                    this.PointBuffer.push(minRad*Math.sin(theta));
                    this.PointBuffer.push(0.0);
                    this.PointBuffer.push(maxRad*Math.cos(theta));
                    this.PointBuffer.push(maxRad*Math.sin(theta));
                    this.PointBuffer.push(0.0);
                }
                this.VertexPositionBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ARRAY_BUFFER, this.VertexPositionBuffer);
                view.gl.bufferData(view.gl.ARRAY_BUFFER, new Float32Array(this.PointBuffer), view.gl.STATIC_DRAW);
                this.VertexPositionBuffer.itemSize = 3;
                this.VertexPositionBuffer.numItems = this.PointBuffer.length / 3;

                // Now create the fill triangles
                // It would be nice to have a center point,
                // but this would mess up the outline.
                for (var i = 2; i < numEdges; ++i) {
                    cellData.push(0);
                    cellData.push((i-1)*2);
                    cellData.push(i*2);
                }
                this.CellBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ELEMENT_ARRAY_BUFFER, this.CellBuffer);
                view.gl.bufferData(view.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(cellData), view.gl.STATIC_DRAW);
                this.CellBuffer.itemSize = 1;
                this.CellBuffer.numItems = cellData.length;

                // Now the thick line
                for (var i = 0; i < numEdges; ++i) {
                    lineCellData.push(0 + i*2);
                    lineCellData.push(1 + i*2);
                    lineCellData.push(2 + i*2);
                    lineCellData.push(1 + i*2);
                    lineCellData.push(3 + i*2);
                    lineCellData.push(2 + i*2);
                }
                this.LineCellBuffer = view.gl.createBuffer();
                view.gl.bindBuffer(view.gl.ELEMENT_ARRAY_BUFFER, this.LineCellBuffer);
                view.gl.bufferData(view.gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(lineCellData), view.gl.STATIC_DRAW);
                this.LineCellBuffer.itemSize = 1;
                this.LineCellBuffer.numItems = lineCellData.length;
            }
        } else {
            for (var i = 0; i <= numEdges; ++i) {
                var theta = i*2*3.14159265359/numEdges;
                this.PointBuffer.push(this.Radius*Math.cos(theta));
                this.PointBuffer.push(this.Radius*Math.sin(theta));
                this.PointBuffer.push(0.0);
            }
        }
    }

    SAM.Circle = Circle;

})();
