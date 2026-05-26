import React, { useState } from 'react';
import { FileText, Code2, BarChart3, Award, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import ScoreGauge from './ScoreGauge';

const TABS = [
  { id: 'ocr', label: 'OCR Text', icon: FileText },
  { id: 'diagram', label: 'Diagram JSON', icon: Code2 },
  { id: 'evaluation', label: 'Evaluation', icon: BarChart3 },
  { id: 'score', label: 'Final Score', icon: Award },
];

export default function ResultsPanel({ result }) {
  const [activeTab, setActiveTab] = useState('evaluation');

  if (!result) return null;

  const ocrText = result.ocr_text;
  const diagramJson = result.diagram_json;
  const theoryEval = result.evaluation?.theory;
  const diagramBonus = result.evaluation?.diagram_bonus;
  const scoreFusion = result.evaluation?.score_fusion;

  const renderContent = () => {
    switch (activeTab) {
      case 'ocr':
        return (
          <div className="results-ocr">
            <div className="ocr-section">
              <h4>📝 Extracted Theory Text</h4>
              <div className="ocr-text-box">
                {ocrText?.theory_text || 'No theory text extracted'}
              </div>
            </div>
            {ocrText?.diagram_labels?.length > 0 && (
              <div className="ocr-section">
                <h4>🏷️ Diagram Labels</h4>
                <div className="label-chips">
                  {ocrText.diagram_labels.map((label, i) => (
                    <span key={i} className="label-chip">{label}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'diagram':
        return (
          <div className="results-json">
            <div className="json-viewer">
              <pre>{JSON.stringify(diagramJson || { message: 'No diagram analyzed' }, null, 2)}</pre>
            </div>
          </div>
        );

      case 'evaluation':
        if (theoryEval?.status === 'evaluation_failed') {
          return (
            <div className="results-evaluation">
              <div className="error-banner" style={{ margin: '20px 0', padding: '20px' }}>
                <AlertTriangle size={24} />
                <div>
                  <h4 style={{ marginBottom: '8px', color: 'var(--accent-red)' }}>Evaluation Temporarily Unavailable</h4>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                    The AI grading service is currently overloaded or unavailable (Error: {theoryEval.reason}).<br/>
                    Please try evaluating again in a few moments.
                  </p>
                </div>
              </div>
            </div>
          );
        }
        
        return (
          <div className="results-evaluation">
            {/* Theory Evaluation */}
            {theoryEval && !theoryEval.error && (
              <div className="eval-card theory-eval-card">
                <div className="eval-card-header">
                  <h4>📖 Theory Evaluation</h4>
                  <span className="eval-score">
                    {theoryEval.score}/{theoryEval.max_score}
                  </span>
                </div>
                
                {/* Key Points */}
                {theoryEval.key_points?.length > 0 && (
                  <div className="key-points">
                    <h5>Key Concepts</h5>
                    {theoryEval.key_points.map((kp, i) => (
                      <div key={i} className={`key-point ${kp.found ? 'kp-found' : 'kp-missing'}`}>
                        {kp.found ? <CheckCircle size={14} /> : <XCircle size={14} />}
                        <span className="kp-text">{kp.point}</span>
                        {kp.student_text && (
                          <span className="kp-student-text">"{kp.student_text}"</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Strengths & Weaknesses */}
                <div className="eval-feedback-grid">
                  {theoryEval.strengths?.length > 0 && (
                    <div className="feedback-col strengths-col">
                      <h5>✅ Strengths</h5>
                      <ul>
                        {theoryEval.strengths.map((s, i) => <li key={i}>{s}</li>)}
                      </ul>
                    </div>
                  )}
                  {theoryEval.weaknesses?.length > 0 && (
                    <div className="feedback-col weaknesses-col">
                      <h5>⚠️ Weaknesses</h5>
                      <ul>
                        {theoryEval.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                      </ul>
                    </div>
                  )}
                </div>

                {theoryEval.overall_feedback && (
                  <div className="overall-feedback">
                    <p>{theoryEval.overall_feedback}</p>
                  </div>
                )}
              </div>
            )}

            {/* Diagram Bonus */}
            {diagramBonus && (
              <div className="eval-card diagram-eval-card">
                <div className="eval-card-header">
                  <h4>🎨 Diagram Bonus</h4>
                  <span className="eval-score bonus-score">
                    +{diagramBonus.bonus_awarded}/{diagramBonus.max_bonus}
                  </span>
                </div>
                {diagramBonus.diagram_quality && (
                  <div className={`quality-badge quality-${diagramBonus.diagram_quality}`}>
                    {diagramBonus.diagram_quality}
                  </div>
                )}
                {diagramBonus.feedback?.length > 0 && (
                  <ul className="bonus-feedback">
                    {diagramBonus.feedback.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                )}
              </div>
            )}
          </div>
        );

      case 'score':
        if (scoreFusion?.status === 'evaluation_failed') {
           return (
            <div className="results-score">
              <div className="error-banner" style={{ margin: '20px 0', padding: '20px', width: '100%', justifyContent: 'center' }}>
                <AlertTriangle size={20} />
                <span>Score calculation pending retry.</span>
              </div>
            </div>
           );
        }
        
        return scoreFusion ? (
          <div className="results-score">
            <ScoreGauge
              score={scoreFusion.final_score}
              maxScore={scoreFusion.max_possible}
              theoryScore={scoreFusion.theory_score}
              maxTheory={scoreFusion.max_theory}
              diagramBonus={scoreFusion.diagram_bonus}
              maxBonus={scoreFusion.max_bonus}
            />
            <div className="score-summary-text">
              {scoreFusion.summary}
            </div>
          </div>
        ) : (
          <div className="results-empty">No score data available</div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="results-panel">
      <div className="results-tabs">
        {TABS.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`results-tab ${activeTab === tab.id ? 'results-tab-active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      <div className="results-content">
        {renderContent()}
      </div>
    </div>
  );
}
