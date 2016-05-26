//==============================================================================
// A single widget to detect multiple sections on a slide
// TODO:
// - Only show the sections tool when you have edit privaleges.
// - Automatically save sections (when advancing)
// - Processing feedback when saving.
// - implement an undo.
// -- save start section in stack
// -- slider in stack viewer.

// - Stack editor.
//   ? Should we save the SectionsWidget in addition to the stackSectionWidget??????
//   ? Default to multiple??????.
// - Improve the deformable registration to handle multiple contours.
// - Extend the rigid outlier code to work with deformable.
// - ScrollWheel to change the threshold of a section.
// - edit the sequence of numbers (somehow).
// - WHen mouse leaves window, cancel the bbox drag.

// I do not like the following behavior:
// Real widgets are always in the viewer.
// Widgets waiting in notes are serialized.


(function () {
    // Depends on the CIRCLE widget
    "use strict";

    function SectionsWidget (viewer, newFlag) {
        if (viewer == null) {
            return;
        }

        var parent = viewer.MainView.CanvasDiv;

        this.Type = "sections";
        this.Viewer = viewer;
        this.Layer = viewer.GetAnnotationLayer();
        this.Layer.AddWidget(this);

        var self = this;

        this.Sections = [];
        this.Active = false;
        this.Layer.EventuallyDraw();
        this.Viewer.EventuallyRender();

        this.ActiveSection = null;
        this.DragBounds = null;
        this.DragViewBounds = null;

        // Just one delete button.
        // Just move it around with the active section.
        this.DeleteButton = $('<img>')
            .appendTo(parent)
            .hide()
            .css({'height': '20px',
                  'position': 'absolute',
                  'z-index': '5'})
            .attr('src',SA.ImagePathUrl+"deleteSmall.png")
            .click(function(){
                self.DeleteActiveSection();
            });

        // Right click menu.
        this.Menu = $('<div>')
            .appendTo(parent)
            .hide()
            .css({
                'width': '150px',
                'background-color': 'white',
                'border-style': 'solid',
                'border-width': '1px',
                'border-radius': '5px',
                'border-color': '#BBB',
                'position': 'absolute',
                'z-index': '4',
                'padding': '0px 2px'});
        $('<button>')
            .appendTo(this.Menu)
            .text("Horizontal Sort")
            .css({'margin':'2px 0px',
                  'width' : '100%'})
            .mouseup(function(){self.Menu.hide(); self.Sort(0);});
        $('<button>')
            .appendTo(this.Menu)
            .text("Vertical Sort")
            .css({'margin':'2px 0px',
                  'width' : '100%'})
            .mouseup(function(){self.Menu.hide(); self.Sort(1);});
    }


    SectionsWidget.prototype.ComputeSections = function() {
        var data = GetImageData(this.Viewer.MainView);
        // slow: SmoothDataAlphaRGB(data, 2);
        var histogram = ComputeIntensityHistogram(data, true);
        var threshold = PickThreshold(histogram);
        console.log("Threshold; " + threshold);
        // TODO: Move the hagfish specific method in to this class.
        var contours = GetHagFishContours(data, threshold, 0.0001, 0.5);
        console.log("num contours: " + contours.length);

        for (var i = 0; i < contours.length; ++i) {
            this.Sections.push(contours[i].MakeStackSectionWidget());
        }

        // Merge close contours int a single section.
        this.MergeCloseSections(0);

        console.log("num merge: " + this.Sections.length);

        // TODO: Simplify args by making x axis = 1, and sign code for direction.
        this.ViewSortSections(1,-1, 0,1);

        this.CreationCamera = this.Layer.GetCamera().Serialize();
    }


    // Get union of all section bounds.
    SectionsWidget.prototype.GetBounds = function() {
        if (this.Sections.length == 0){ return [0,0,0,0]; }
        var allBds = this.Sections[0].GetBounds();
        for (var i = 0; i < this.Sections.length; ++i) {
            var bds = this.Sections[i].GetBounds();
            if (bds[0] < allBds[0]) { allBds[0] = bds[0];}
            if (bds[1] > allBds[1]) { allBds[1] = bds[1];}
            if (bds[2] < allBds[2]) { allBds[2] = bds[2];}
            if (bds[3] > allBds[3]) { allBds[3] = bds[3];}
        }
        return allBds;
    }

    // Gets direction from the active section.
    SectionsWidget.prototype.Sort = function(axis) {
        var axis0 = 0;
        var axis1 = 1;
        var direction0 = 1;
        var direction1 = 1;
        if (this.ActiveSection) {
            var allBds = this.GetBounds();
            var allCenter = this.Layer.ConvertPointWorldToViewer(
                (allBds[0]+allBds[1])*0.5, (allBds[0]+allBds[1])*0.5);
            var center = this.ActiveSection.GetViewCenter(this.Viewer.MainView);
            if (center[0] < allCenter[0]) {
                direction0 = -1;
            }
            if (center[1] < allCenter[1]) {
                direction1 = -1;
            }
        }
        if (axis == 1) {
            var tmp = direction0;
            direction0 = direction1;
            direction1 = tmp;
            axis0 = 1;
            axis1 = 0;
        }
        this.ViewSortSections(axis0,direction0, axis1,direction1);
    }

    SectionsWidget.prototype.ViewSortSections = function(axis0,direction0, 
                                                         axis1,direction1) {
        function lessThan(bds1,bds2) {
            if ((bds1[(axis1<<1)+1] > bds2[axis1<<1]) &&
                ((bds1[axis1<<1] > bds2[(axis1<<1)+1] ||
                  bds1[axis0<<1] > bds2[(axis0<<1)+1]))) {
                return true;
            }
            return false;
        }
        // Compute and save view bounds for each section.
        for (var i = 0; i < this.Sections.length; ++i) {
            var section = this.Sections[i];
            section.ViewBounds = section.GetViewBounds(this.Viewer.MainView);
            PermuteBounds(section.ViewBounds, axis0, direction0);
            PermuteBounds(section.ViewBounds, axis1, direction1);
        }

        // Use lessThan to sort (insertion).
        for (var i = 1; i < this.Sections.length; ++i) {
            var bestBds = this.Sections[i-1].ViewBounds;
            var bestIdx = -1;
            for (var j = i; j < this.Sections.length; ++j) {
                var bds = this.Sections[j].ViewBounds;
                if (lessThan(bds, bestBds)) {
                    bestBds = bds;
                    bestIdx = j;
                }
            }
            if (bestIdx > 0) {
                var tmp = this.Sections[bestIdx];
                this.Sections[bestIdx] = this.Sections[i-1];
                this.Sections[i-1] = tmp;
            }
        }
        this.Layer.EventuallyDraw();
    }

    SectionsWidget.prototype.DeleteActiveSection = function() {
        if (this.ActiveSection == null) { return; }
        var section = this.ActiveSection;
        this.SetActiveSection(null);
        this.RemoveSection(section);
        if (this.IsEmpty()) {
            this.RemoveFromViewer();
            this.Layer.EventuallyDraw();
            if (window.SA) {SA.RecordState();}
        }
    }

    SectionsWidget.prototype.RemoveSection = function(section) {
        if (this.ActiveSection == section) this.ActiveSection = null;
        var idx = this.Sections.indexOf(section);
        if (idx > -1) {
            this.Sections.splice(idx,1);
        }
    }


    SectionsWidget.prototype.SetActiveSection = function(section) {
        if (section == this.ActiveSection) { return;}

        if (this.ActiveSection) {
            this.ActiveSection.Active = false;
            this.DeleteButton.hide();
        } else {
            section.Active = true;
            this.DeleteButton.show();
            // Draw moves it to the correct location.
        }
        this.ActiveSection = section;
        this.Layer.EventuallyDraw();
    }


    SectionsWidget.prototype.PlaceDeleteButton = function(section) {
        if (section) {
            var p = section.ViewUpperRight;
            this.DeleteButton
                .show()
                .css({'left': (p[0]-10)+'px',
                      'top':  (p[1]-10)+'px'});
        }
    }

    // world is a boolean indicating the bounds should be drawn in slide coordinates. 
    SectionsWidget.prototype.DrawBounds = function(view, bds, world, color) {
        var pt0 = [bds[0],bds[2]];
        var pt1 = [bds[1],bds[2]];
        var pt2 = [bds[1],bds[3]];
        var pt3 = [bds[0],bds[3]];

        if (world) {
            pt0 = view.Camera.ConvertPointWorldToViewer(pt0[0],pt0[1]);
            pt1 = view.Camera.ConvertPointWorldToViewer(pt1[0],pt1[1]);
            pt2 = view.Camera.ConvertPointWorldToViewer(pt2[0],pt2[1]);
            pt3 = view.Camera.ConvertPointWorldToViewer(pt3[0],pt3[1]);
        }
        var ctx = view.Context2d;
        ctx.save();
        ctx.setTransform(1,0,0,1,0,0);
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.moveTo(pt0[0], pt0[1]);
        ctx.lineTo(pt1[0], pt1[1]);
        ctx.lineTo(pt2[0], pt2[1]);
        ctx.lineTo(pt3[0], pt3[1]);
        ctx.lineTo(pt0[0], pt0[1]);
        ctx.stroke();
        ctx.restore();
    }

    SectionsWidget.prototype.Draw = function(view) {
        if ( ! this.Active) {
            return;
        }
        for (var i = 0; i < this.Sections.length; ++i) {
            var section = this.Sections[i];
            section.Draw(view);
            // Draw the section index.
            var pt = section.ViewUpperRight;
            var ctx = view.Context2d;
            ctx.save();
            ctx.setTransform(1,0,0,1,0,0);
            ctx.font="20px Georgia";
            ctx.fillStyle='#00F';
            ctx.fillText((i+1).toString(),pt[0]-10,pt[1]+25);
            ctx.restore();
        }
        if (this.ActiveSection) {
            this.PlaceDeleteButton(this.ActiveSection);
        }
        if (this.ActiveSection) {
            var bds = this.ActiveSection.GetBounds();
            this.DrawBounds(view,bds,true,'#FF0');
        }
        if (this.DragBounds) {
        this.DrawBounds(view,this.DragBounds,true, '#F00');
        }
    }


    SectionsWidget.prototype.Serialize = function() {
        var obj = new Object();
        obj.type = "sections";
        obj.sections = [];
        for (var i = 0; i < this.Sections.length; ++i) {
            var section = this.Sections[i].Serialize();
            obj.sections.push(section);
        }
        // Already serialized
        obj.creation_camera = this.CreationCamera;

        return obj;
    }

    // Load a widget from a json object (origin MongoDB).
    SectionsWidget.prototype.Load = function(obj) {
        for(var n=0; n < obj.sections.length; n++){
            var section = new SAM.StackSectionWidget();
            section.Load(obj.sections[n]);
            if ( ! section.IsEmpty()) {
                this.Sections.push(section);
            }
        }
        this.CreationCamera = obj.creation_camera;
        if (this.IsEmpty()) {
            this.RemoveFromViewer();
        }
    }

    SectionsWidget.prototype.IsEmpty = function() {
        return this.Sections.length == 0;
    }

    SectionsWidget.prototype.HandleMouseWheel = function(event) {
        return true;
    }

    SectionsWidget.prototype.HandleKeyPress = function(event, shift) {
        if (event.keyCode == 46) {
            this.DeleteActiveSection();
            return false;
        }
        return true;
    }

    SectionsWidget.prototype.HandleMouseDown = function(event) {
        this.StartX = event.offsetX;
        this.StartY = event.offsetY;
        if (this.ActiveSection) {
            if (event.which == 3) {
                this.Menu
                    .show()
                    .css({'left': event.offsetX+'px',
                          'top' : event.offsetY+'px'});
            }
            return false;
        }
        return true;
    }

    SectionsWidget.prototype.HandleMouseUp = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;
        if (event.which == 1) {
            if (Math.abs(x-this.StartX) +
                Math.abs(y-this.StartY) < 5) {
                //alert("click");
            } else if (this.DragBounds) {
                this.ProcessBounds(this.DragBounds);
            }
            this.DragBounds = null;
            this.Layer.EventuallyDraw();
        }
        this.Menu.hide();
        return false;
    }

    SectionsWidget.prototype.HandleDoubleClick = function(event) {
        return true;
    }

    SectionsWidget.prototype.HandleMouseMove = function(event) {
        var x = event.offsetX;
        var y = event.offsetY;
        if (event.which == 1) {
            // Drag out a bounding box.
            // Keep the bounding box in slide coordinates for now.
            var pt0 = this.Viewer.ConvertPointViewerToWorld(this.StartX, this.StartY);
            var pt1 = this.Viewer.ConvertPointViewerToWorld(x, y);
            this.DragBounds = [pt0[0],pt1[0], pt0[1],pt1[1]];
            this.Layer.EventuallyDraw();
            return false;
        }

        if (event.which == 0) {
            var pt = this.Viewer.ConvertPointViewerToWorld(x,y);
            // Find the smallest section with pt in the bbox.
            var bestSection = null;
            var bestArea = -1;
            for (var i = 0; i < this.Sections.length; ++i) {
                var bds = this.Sections[i].GetBounds();
                if (pt[0]>bds[0] && pt[0]<bds[1] && pt[1]>bds[2] && pt[1]<bds[3]) {
                    var area = (bds[1]-bds[0])*(bds[3]-bds[2]);
                    if (bestSection == null || area < bestArea) {
                        bestSection = this.Sections[i];
                        bestArea = area;
                    }
                }
            }
            this.SetActiveSection(bestSection);
            return true;
        }
    }

    SectionsWidget.prototype.CheckActive = function(event) {
        return this.Active;
    }

    SectionsWidget.prototype.GetActive = function() {
        return this.Active;
    }

    // Setting to active always puts state into "active".
    // It can move to other states and stay active.
    SectionsWidget.prototype.SetActive = function(flag) {
        if (flag) {
            this.Layer.ActivateWidget(this);
            this.Active = true;
        } else {
            this.Layer.DeactivateWidget(this);
            this.Active = false;
            if (this.DeactivateCallback) {
                this.DeactivateCallback();
            }
        }
        this.Layer.EventuallyDraw();
    }

    SectionsWidget.prototype.Deactivate = function() {
        this.SetActive(false);
    }

    // The multiple actions of bounds might be confusing to the user.
    SectionsWidget.prototype.ProcessBounds = function(bds) {
        if (bds[0] > bds[1]) {
            var tmp = bds[0];
            bds[0] = bds[1];
            bds[1] = tmp;
        }
        if (bds[2] > bds[3]) {
            var tmp = bds[2];
            bds[2] = bds[3];
            bds[3] = tmp;
        }

        var full = [];
        var partial = [];
        for (var i = 0; i < this.Sections.length; ++i) {
            var section = this.Sections[i];
            var mode = section.ContainedInBounds(bds);
            if (mode == 2) { full.push(section); }
            if (mode == 1) { partial.push(section); }
        }
        // If the rectangle fully contains more than one shape, group them
        if (full.length > 1) {
            for (var i = 1; i < full.length; ++i) {
                full[0].Union(full[i]);
                this.RemoveSection(full[i]);
            }
        }
        // If bounds do not contain any section, process the image for a new one.
        if (full.length == 0 && partial.length == 0) {
            // My decision to keep bounds in slide space is causing problems
            // here. I might want to change all bounds comparison to view.
            // It would require recomputation of bounds when the view changes,
            // but that would not be too expensive.  It would require a
            // view change event to invalidate all bounds.
            // For now just get the data in view coordinates.
            // Compute the resolution.
            var self = this;
            var scale = (bds[1]-bds[0]+bds[3]-bds[2]) / 600;
            if (scale < 1) { scale = 1; }

            GetCutoutImage(this.Viewer.GetCache(),
                           [Math.round((bds[1]-bds[0])/scale), Math.round((bds[3]-bds[2])/scale)],
                           [0.5*(bds[0]+bds[1]), 0.5*(bds[2]+bds[3])],
                           scale, 0, null,
                           function (data) {
                               // slow: SmoothDataAlphaRGB(data, 2);
                               var histogram = ComputeIntensityHistogram(data, true);
                               var threshold = PickThreshold(histogram);
                               // TODO: Move the hagfish specific method in to this class.
                               var contours = self.GetBigContours(data, threshold);
                               if (contours.length == 0) { return; }
                               var w = new SAM.StackSectionWidget();
                               for (var i = 0; i < contours.length; ++i) {
                                   w.Shapes.push(contours[i].MakePolyline([0,1,0]));
                               }
                               self.Sections.push(w);
                               this.Layer.EventuallyDraw();
                           });
        }

        // If the contours partially contains only one section, and clean
        // separates the shapes, then split them.
        if (full.length == 0 && partial.length == 1) {
            var section = partial[0];
            full = [];
            partial = [];
            for (var i = 0; i < section.Shapes.length; ++i) {
                var contains = section.Shapes[i].ContainedInBounds(bds);
                if (contains == 1) { partial.push(section.Shapes[i]); }
                if (contains == 2) { full.push(section.Shapes[i]); }
            }
            if (partial.length == 0) {
                var idx;
                // Split it up.
                var newSection = new SAM.StackSectionWidget();
                newSection.Shapes = full;
                for (var i = 0; i < full.length; ++i) {
                    idx = section.Shapes.indexOf(full[i]);
                    if (idx != -1) {
                        section.Shapes.splice(idx,1);
                    }
                    section.Bounds = null;
                }
                idx = this.Sections.indexOf(section);
                this.Sections.splice(idx,0,newSection);
            }
        }
    }


    // Returns all contours (including inside out contours).
    SectionsWidget.prototype.GetContours = function (data, threshold) {
        // Loop over the cells.
        // Start at the bottom left: y up then x right.
        // (The order of sections on the hagfish slides.)
        var contours = [];
        for (var x = 1; x < data.width; ++x) {
            for (var y = 1; y < data.height; ++y) {
                // Look for contours crossing the xMax and yMax edges.
                var xContour = SeedIsoContour(data, x,y, x-1,y, threshold);
                if (xContour) {
                    var c = new SA.Contour();
                    c.Camera = data.Camera;
                    c.Threshold = threshold;
                    c.SetPoints(xContour);
                    c.RemoveDuplicatePoints(2);
                    var area = c.GetArea();
                    contours.push(c);
                }

                var yContour = SeedIsoContour(data, x,y, x,y-1, threshold);
                if (yContour) {
                    c = new SA.Contour();
                    c.Camera = data.Camera;
                    c.Threshold = threshold;
                    c.SetPoints(yContour);
                    c.RemoveDuplicatePoints(2);
                    area = c.GetArea();
                    contours.push(c);
                }
            }
        }
        return contours;
    }


    // Returns all contours at least 50% the area of the largest contour.
    SectionsWidget.prototype.GetBigContours = function (data, threshold) {
        var contours = this.GetContours(data, threshold);

        // Area is cached in the contour object.
        var largestArea = 0;
        for (var i = 0; i < contours.length; ++i) {
            if (contours[i].GetArea() > largestArea) {
                largestArea = contours[i].GetArea();
            }
        }

        var bigContours = [];
        for (var i = 0; i < contours.length; ++i) {
            if (contours[i].GetArea() > largestArea*0.5) {
                bigContours.push(contours[i]);
            }
        }

        return bigContours;
    }


    // Just use bounds for now.  Computing actual distances will be complex.
    SectionsWidget.prototype.MergeCloseSections = function(dist) {
        for (var i = 0; i < this.Sections.length; ++i) {
            var section = this.Sections[i];
            for (j = i+1; j < this.Sections.length; ++j) {
                var other = this.Sections[j];
                var bds0 = section.GetBounds();
                var bds1 = other.GetBounds();
                if (bds0[1]+dist > bds1[0] && bds0[0]-dist < bds1[1] &&
                    bds0[3]+dist > bds1[2] && bds0[2]-dist < bds1[3]) {
                    section.Union(other);
                    this.Sections.splice(j,1);
                    section
                    --j;
                }
            }
        }
    }

    SAM.SectionsWidget = SectionsWidget;

})();
