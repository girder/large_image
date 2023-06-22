// Modified from https://www.w3schools.com/howto/howto_js_draggable.asp

import clamp from './clamp';

export function makeDraggableSVG(svg, validateDrag, callback, xRange) {
    let selectedShape;
    let posOffset;
    svg.addEventListener('mousedown', startDrag);
    window.addEventListener('mousemove', drag);
    window.addEventListener('mouseup', endDrag);

    function getMousePosition(evt) {
        if (!svg) return {x: 0, y: 0};
        const CTM = svg.getScreenCTM();
        if (!CTM) return {x: 0, y: 0};
        return {
            x: (evt.clientX - CTM.e) / CTM.a,
            y: (evt.clientY - CTM.f) / CTM.d
        };
    }

    function startDrag(evt) {
        const target = evt.target;
        if (target && target.classList.contains('draggable')) {
            selectedShape = target;
            posOffset = getMousePosition(evt);
            posOffset.x -= parseFloat(
                selectedShape.getAttributeNS(null, 'x1') || '0'
            );
            posOffset.y -= parseFloat(
                selectedShape.getAttributeNS(null, 'y1') || '0'
            );
        }
    }

    function drag(evt) {
        if (selectedShape) {
            evt.preventDefault();
            const coord = getMousePosition(evt);
            if (posOffset) {
                coord.x -= posOffset.x;
                coord.y -= posOffset.y;
            }
            coord.x = clamp(coord.x, xRange[0], xRange[1]);
            const [moveX, moveY] = validateDrag(selectedShape, coord);
            if (!moveX) {
                coord.x = parseFloat(selectedShape.getAttributeNS(null, 'x1') || '0');
            }
            if (!moveY) {
                coord.y = parseFloat(selectedShape.getAttributeNS(null, 'y1') || '0');
            }

            selectedShape.setAttributeNS(null, 'x1', `${coord.x}`);
            selectedShape.setAttributeNS(null, 'x2', `${coord.x}`);
            selectedShape.setAttributeNS(null, 'y1', `${coord.y}`);
            callback(selectedShape, coord);
        }
    }
    function endDrag() {
        selectedShape = undefined;
    }
}
