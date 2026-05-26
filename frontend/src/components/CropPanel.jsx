import React, { useState } from 'react';
import { Image as ImageIcon, FileText, Tag, ArrowRight } from 'lucide-react';

const TABS = [
  { id: 'theory', label: 'Theory Crop', icon: FileText },
  { id: 'diagram', label: 'Diagram Crop', icon: ImageIcon },
  { id: 'labels', label: 'Labels', icon: Tag },
  { id: 'connectors', label: 'Connectors', icon: ArrowRight },
];

export default function CropPanel({ crops, diagramOverlay }) {
  const [activeTab, setActiveTab] = useState('theory');

  const theoryCrop = crops?.theory_crop;
  const diagramCrop = crops?.diagram_crop;
  const labelRegions = crops?.label_regions || [];
  const connectorRegions = crops?.connector_regions || [];

  const renderContent = () => {
    switch (activeTab) {
      case 'theory':
        return theoryCrop ? (
          <div className="crop-image-wrapper">
            <img src={theoryCrop} alt="Theory Text Crop" className="crop-image" />
          </div>
        ) : (
          <EmptyState icon={FileText} text="No theory text region detected" />
        );

      case 'diagram':
        return diagramCrop ? (
          <div className="crop-image-wrapper diagram-crop-wrapper">
            <img src={diagramCrop} alt="Diagram Crop" className="crop-image" />
            {diagramOverlay && (
              <img
                src={diagramOverlay}
                alt="Diagram Overlay"
                className="crop-overlay"
              />
            )}
          </div>
        ) : (
          <EmptyState icon={ImageIcon} text="No diagram detected on this page" />
        );

      case 'labels':
        return labelRegions.length > 0 ? (
          <div className="regions-list">
            {labelRegions.map((r, i) => (
              <div key={i} className="region-card label-card">
                <Tag size={14} />
                <span>{r.description || `Label region ${i + 1}`}</span>
                <span className="confidence-badge">
                  {Math.round((r.confidence || 0) * 100)}%
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={Tag} text="No diagram labels detected" />
        );

      case 'connectors':
        return connectorRegions.length > 0 ? (
          <div className="regions-list">
            {connectorRegions.map((r, i) => (
              <div key={i} className="region-card connector-card">
                <ArrowRight size={14} />
                <span>{r.description || `Connector ${i + 1}`}</span>
                <span className="confidence-badge">
                  {Math.round((r.confidence || 0) * 100)}%
                </span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon={ArrowRight} text="No connectors detected" />
        );

      default:
        return null;
    }
  };

  return (
    <div className="crop-panel">
      <div className="panel-header">
        <span className="panel-title">
          <ImageIcon size={18} />
          <span>Detected Regions</span>
        </span>
      </div>

      {/* Tabs */}
      <div className="crop-tabs">
        {TABS.map(tab => {
          const Icon = tab.icon;
          let count = 0;
          if (tab.id === 'theory') count = theoryCrop ? 1 : 0;
          if (tab.id === 'diagram') count = diagramCrop ? 1 : 0;
          if (tab.id === 'labels') count = labelRegions.length;
          if (tab.id === 'connectors') count = connectorRegions.length;

          return (
            <button
              key={tab.id}
              className={`crop-tab ${activeTab === tab.id ? 'crop-tab-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
              {count > 0 && <span className="tab-count">{count}</span>}
            </button>
          );
        })}
      </div>

      <div className="crop-content">
        {renderContent()}
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, text }) {
  return (
    <div className="crop-empty">
      <Icon size={32} className="crop-empty-icon" />
      <p>{text}</p>
    </div>
  );
}
