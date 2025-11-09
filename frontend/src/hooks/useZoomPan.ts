import { useState, useCallback, useRef, useEffect } from 'react';

export interface ZoomPanState {
  zoom: number;  // 0.5 to 2.0 (50% to 200%)
  panX: number;
  panY: number;
}

interface UseZoomPanProps {
  minZoom?: number;
  maxZoom?: number;
  initialZoom?: number;
}

export const useZoomPan = ({
  minZoom = 0.5,
  maxZoom = 2.0,
  initialZoom = 1.0,
}: UseZoomPanProps = {}) => {
  const [state, setState] = useState<ZoomPanState>({
    zoom: initialZoom,
    panX: 0,
    panY: 0,
  });

  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState<[number, number] | null>(null);
  const [spacePressed, setSpacePressed] = useState(false);
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Clamp zoom value
  const clampZoom = useCallback((zoom: number): number => {
    return Math.max(minZoom, Math.min(maxZoom, zoom));
  }, [minZoom, maxZoom]);

  // Handle mouse wheel zoom (centered on cursor)
  const handleWheel = useCallback((event: WheelEvent) => {
    event.preventDefault();
    
    const svg = svgRef.current;
    if (!svg) return;

    // Get mouse position relative to SVG
    const rect = svg.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    // Get current viewBox
    const viewBox = svg.viewBox.baseVal;
    const currentWidth = viewBox.width;
    const currentHeight = viewBox.height;

    // Calculate zoom factor
    const delta = event.deltaY > 0 ? 0.9 : 1.1;
    const newZoom = clampZoom(state.zoom * delta);

    // Calculate zoom change
    const zoomChange = newZoom / state.zoom;

    // Calculate new viewBox dimensions
    const newWidth = currentWidth / zoomChange;
    const newHeight = currentHeight / zoomChange;

    // Calculate mouse position in SVG coordinates (before zoom)
    const svgX = (mouseX / rect.width) * currentWidth + viewBox.x;
    const svgY = (mouseY / rect.height) * currentHeight + viewBox.y;

    // Calculate new pan to keep mouse position fixed
    const newPanX = svgX - (mouseX / rect.width) * newWidth;
    const newPanY = svgY - (mouseY / rect.height) * newHeight;

    setState({
      zoom: newZoom,
      panX: newPanX,
      panY: newPanY,
    });
  }, [state.zoom, clampZoom]);

  // Handle pan start (spacebar + mouse down or middle mouse)
  const handlePanStart = useCallback((event: React.MouseEvent<SVGElement>) => {
    if (event.button === 1 || spacePressed) {
      event.preventDefault();
      setIsPanning(true);
      setPanStart([event.clientX, event.clientY]);
    }
  }, [spacePressed]);

  // Handle pan move
  const handlePanMove = useCallback((event: React.MouseEvent<SVGElement>) => {
    if (!isPanning || !panStart) return;

    const svg = svgRef.current;
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    const viewBox = svg.viewBox.baseVal;

    // Calculate pan delta in SVG coordinates
    const deltaX = (event.clientX - panStart[0]) * (viewBox.width / rect.width);
    const deltaY = (event.clientY - panStart[1]) * (viewBox.height / rect.height);

    setState(prev => ({
      ...prev,
      panX: prev.panX - deltaX,
      panY: prev.panY - deltaY,
    }));

    setPanStart([event.clientX, event.clientY]);
  }, [isPanning, panStart]);

  // Handle pan end
  const handlePanEnd = useCallback(() => {
    setIsPanning(false);
    setPanStart(null);
  }, []);

  // Reset zoom/pan to fit screen
  const resetZoom = useCallback(() => {
    setState({
      zoom: initialZoom,
      panX: 0,
      panY: 0,
    });
  }, [initialZoom]);

  // Zoom in
  const zoomIn = useCallback(() => {
    setState(prev => ({
      ...prev,
      zoom: clampZoom(prev.zoom * 1.2),
    }));
  }, [clampZoom]);

  // Zoom out
  const zoomOut = useCallback(() => {
    setState(prev => ({
      ...prev,
      zoom: clampZoom(prev.zoom / 1.2),
    }));
  }, [clampZoom]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.code === 'Space' && event.target === document.body) {
        event.preventDefault();
        setSpacePressed(true);
      } else if (event.ctrlKey || event.metaKey) {
        if (event.key === '0') {
          event.preventDefault();
          resetZoom();
        } else if (event.key === '=' || event.key === '+') {
          event.preventDefault();
          zoomIn();
        } else if (event.key === '-') {
          event.preventDefault();
          zoomOut();
        }
      }
    };

    const handleKeyUp = (event: KeyboardEvent) => {
      if (event.code === 'Space') {
        setSpacePressed(false);
        if (isPanning) {
          handlePanEnd();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [resetZoom, zoomIn, zoomOut, isPanning, handlePanEnd]);

  // Prevent middle mouse button from scrolling
  useEffect(() => {
    const handleContextMenu = (event: MouseEvent) => {
      if (event.button === 1) {
        event.preventDefault();
      }
    };

    const handleMouseDown = (event: MouseEvent) => {
      if (event.button === 1) {
        event.preventDefault();
      }
    };

    window.addEventListener('contextmenu', handleContextMenu);
    window.addEventListener('mousedown', handleMouseDown);

    return () => {
      window.removeEventListener('contextmenu', handleContextMenu);
      window.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  // Add wheel event listener
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    svg.addEventListener('wheel', handleWheel, { passive: false });

    return () => {
      svg.removeEventListener('wheel', handleWheel);
    };
  }, [handleWheel]);

  return {
    state,
    svgRef,
    isPanning,
    spacePressed,
    handleWheel,
    handlePanStart,
    handlePanMove,
    handlePanEnd,
    resetZoom,
    zoomIn,
    zoomOut,
  };
};

