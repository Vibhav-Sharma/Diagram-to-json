import React, { useState } from 'react';
import { Eye, EyeOff, Layers } from 'lucide-react';

const REGION_COLORS = {
  theory_text: { fill: 'rgba(59, 130, 246, 0.15)', stroke: '#3b82f6', label: 'Theory Text' },
  diagram: { fill: 'rgba(168, 85, 247, 0.15)', stroke: '#a855f7', label: 'Diagram' },
  diagram_label: { fill: 'rgba(245, 158, 11, 0.15)', stroke: '#f59e0b', label: 'Label' },
  connector: { fill: 'rgba(34, 197, 94, 0.15)', stroke: '#22c55e', label: 'Connector' },
  question_text: { fill: 'rgba(107, 114, 128, 0.15)', stroke: '#6b7280', label: 'Question' },
};

export default function ImagePanel({ previewUrl, segmentation }) {
  const [showOverlay, setShowOverlay] = useState(true);
  const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0 });

  const regions = segmentation?.regions || [];

  const handleImageLoad = (e) => {
    setImgDimensions({
      width: e.target.naturalWidth,
      height: e.target.naturalHeight,
    });
  };

  return (
    <div className="image-panel">
      <div className="panel-header">
        <div className="panel-title">
          <Layers size={18} />
          <span>Original Answer Sheet</span>
        </div>
        {regions.length > 0 && (
          <button
            className="overlay-toggle"
            onClick={() => setShowOverlay(!showOverlay)}
          >
            {showOverlay ? <EyeOff size={16} /> : <Eye size={16} />}
            <span>{showOverlay ? 'Hide' : 'Show'} Regions</span>
          </button>
        )}
      </div>

      <div className="image-container">
        {previewUrl ? (
          <div className="image-wrapper">
            <img
              src={previewUrl}
              alt="Answer Sheet"
              className="answer-image"
              onLoad={handleImageLoad}
            />
            
            {/* Region Overlay Boxes */}
            {showOverlay && regions.map((region, i) => {
              const [ymin, xmin, ymax, xmax] = region.box_2d;
              const colorInfo = REGION_COLORS[region.region_type] || REGION_COLORS.theory_text;
              
              return (
                <div
                  key={i}
                  className="region-box"
                  style={{
                    top: `${ymin / 10}%`,
                    left: `${xmin / 10}%`,
                    width: `${(xmax - xmin) / 10}%`,
                    height: `${(ymax - ymin) / 10}%`,
                    backgroundColor: colorInfo.fill,
                    borderColor: colorInfo.stroke,
                  }}
                >
                  <span
                    className="region-tag"
                    style={{ backgroundColor: colorInfo.stroke }}
                  >
                    {colorInfo.label}
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="image-placeholder">
            <Layers size={48} className="placeholder-icon" />
            <p>Upload an answer sheet to begin</p>
          </div>
        )}
      </div>

      {/* Legend */}
      {showOverlay && regions.length > 0 && (
        <div className="region-legend">
          {Object.entries(REGION_COLORS).map(([key, val]) => {
            const count = regions.filter(r => r.region_type === key).length;
            if (count === 0) return null;
            return (
              <div key={key} className="legend-item">
                <span className="legend-dot" style={{ backgroundColor: val.stroke }} />
                <span>{val.label} ({count})</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
