/**
 * Convert screen coordinates to SVG coordinates accounting for zoom/pan
 */
export const screenToSVG = (
  screenX: number,
  screenY: number,
  svgElement: SVGSVGElement,
  zoom: number = 1,
  panX: number = 0,
  panY: number = 0
): [number, number] => {
  const pt = svgElement.createSVGPoint();
  pt.x = screenX;
  pt.y = screenY;
  
  // Get the screen-to-SVG transform
  const screenCTM = svgElement.getScreenCTM();
  if (!screenCTM) {
    return [screenX, screenY];
  }
  
  // Apply inverse transform
  const svgP = pt.matrixTransform(screenCTM.inverse());
  
  // Account for zoom and pan
  // When zoomed, the viewBox is smaller, so coordinates need adjustment
  // Note: viewBox and rect are available but not directly used here as the
  // matrixTransform already accounts for the viewBox transform
  
  // Calculate the actual SVG coordinate accounting for viewBox transform
  const svgX = (svgP.x - panX) / zoom;
  const svgY = (svgP.y - panY) / zoom;
  
  return [svgX, svgY];
};

/**
 * Convert SVG coordinates to screen coordinates accounting for zoom/pan
 */
export const svgToScreen = (
  svgX: number,
  svgY: number,
  svgElement: SVGSVGElement,
  zoom: number = 1,
  panX: number = 0,
  panY: number = 0
): [number, number] => {
  const pt = svgElement.createSVGPoint();
  
  // Apply zoom and pan
  const transformedX = svgX * zoom + panX;
  const transformedY = svgY * zoom + panY;
  
  pt.x = transformedX;
  pt.y = transformedY;
  
  // Get the SVG-to-screen transform
  const screenCTM = svgElement.getScreenCTM();
  if (!screenCTM) {
    return [transformedX, transformedY];
  }
  
  const screenP = pt.matrixTransform(screenCTM);
  
  return [screenP.x, screenP.y];
};

