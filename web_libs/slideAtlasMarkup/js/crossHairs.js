// cross hairs was created as an anchor for text.
// Just two lines that cross at a point.
// I am not goint to support line width, or fillColor.
// Shape seems to define lines in a loop, so I will create a loop for now.

(function () {
    "use strict";

    function CrossHairs() {
        SAM.Shape.call(this);
        this.Length = 50; // Length of the crosing lines
        this.Width = 1; // Width of the cross hair lines.
        this.Origin = [10000,10000]; // position in world coordinates.
        this.FillColor    = [0,0,0];
        this.OutlineColor = [1,1,1];
        this.PointBuffer = [];
    };
    CrossHairs.prototype = new SAM.Shape;

    CrossHairs.prototype.destructor=function() {
        // Get rid of the buffers?
    }

    CrossHairs.prototype.UpdateBuffers = function(view) {
        this.PointBuffer = [];
        var cellData = [];
        var halfLength = (this.Length * 0.5) + 0.5;
        var halfWidth = (this.Width * 0.5) + 0.5;

        this.Matrix = mat4.create();
        mat4.identity(this.Matrix);

        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfLength);
        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfLength);
        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(halfLength);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(halfLength);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfLength);
        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfLength);
        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(halfWidth);
        this.PointBuffer.push(-halfLength);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(-halfLength);
        this.PointBuffer.push(0.0);

        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(-halfWidth);
        this.PointBuffer.push(0.0);

        cellData.push(1);
        cellData.push(2);
        cellData.push(7);

        cellData.push(1);
        cellData.push(7);
        cellData.push(8);

        cellData.push(4);
        cellData.push(5);
        cellData.push(10);

        cellData.push(4);
        cellData.push(10);
        cellData.push(11);

        if (view.gl) {
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
        }
    }


    SAM.CrossHairs = CrossHairs;

})();
