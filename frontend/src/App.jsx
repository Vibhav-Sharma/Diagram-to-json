import React, { useState } from 'react';
import { AlertCircle, BookOpen } from 'lucide-react';
import UploadSection from './components/UploadSection';
import ImagePanel from './components/ImagePanel';
import CropPanel from './components/CropPanel';
import ResultsPanel from './components/ResultsPanel';

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [pipelineStage, setPipelineStage] = useState('');

  const handleEvaluate = async ({ file, question, autoExtract, maxMarks, previewUrl: pUrl }) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setPreviewUrl(pUrl);
    setPipelineStage('Uploading...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('question', question);
    formData.append('auto_extract_question', autoExtract);
    formData.append('max_marks', maxMarks);

    try {
      setPipelineStage('Running evaluation pipeline...');
      const response = await fetch('http://localhost:8000/evaluate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setPipelineStage('Complete');
    } catch (err) {
      setError(err.message);
      setPipelineStage('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-root">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-brand">
            <BookOpen size={28} />
            <div>
              <h1>Answer Sheet Evaluator</h1>
              <p className="header-subtitle">
                Structured Page Understanding • Theory + Diagram • AI Evaluation
              </p>
            </div>
          </div>
          {loading && (
            <div className="pipeline-status">
              <span className="status-dot" />
              <span>{pipelineStage}</span>
            </div>
          )}
        </div>
      </header>

      <main className="app-main">
        {/* Upload Section */}
        <UploadSection onEvaluate={handleEvaluate} loading={loading} />

        {/* Error Display */}
        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Question Display */}
        {result?.question && (
          <div className="question-display">
            <strong>Question:</strong> {result.question}
            {result?.extracted_question && (
              <span className="auto-extracted-badge">Auto-extracted</span>
            )}
          </div>
        )}

        {/* Main Content: Image Panel + Crop Panel */}
        {(previewUrl || result) && (
          <div className="panels-grid">
            <ImagePanel
              previewUrl={previewUrl}
              segmentation={result?.segmentation}
            />
            {result && (
              <CropPanel
                crops={result.crops}
                diagramOverlay={result.crops?.diagram_overlay}
              />
            )}
          </div>
        )}

        {/* Results Panel */}
        {result && <ResultsPanel result={result} />}
      </main>
    </div>
  );
}

export default App;
