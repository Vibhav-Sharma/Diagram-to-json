import React, { useState } from 'react';
import { Upload, FileText, AlertCircle, Sparkles } from 'lucide-react';

export default function UploadSection({ onEvaluate, loading }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [question, setQuestion] = useState('');
  const [autoExtract, setAutoExtract] = useState(false);
  const [maxMarks, setMaxMarks] = useState(10);
  const [dragActive, setDragActive] = useState(false);

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith('image/')) {
      setFile(dropped);
      setPreviewUrl(URL.createObjectURL(dropped));
    }
  };

  const handleSubmit = () => {
    if (!file) return;
    if (!question.trim() && !autoExtract) return;
    onEvaluate({ file, question, autoExtract, maxMarks, previewUrl });
  };

  return (
    <div className="upload-section">
      {/* File Upload */}
      <div
        className={`dropzone ${dragActive ? 'dropzone-active' : ''} ${previewUrl ? 'dropzone-has-file' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <label className="dropzone-label">
          {previewUrl ? (
            <div className="dropzone-preview">
              <img src={previewUrl} alt="Preview" className="dropzone-thumb" />
              <div className="dropzone-file-info">
                <p className="dropzone-filename">{file?.name}</p>
                <p className="dropzone-hint">Click or drop to change</p>
              </div>
            </div>
          ) : (
            <div className="dropzone-empty">
              <Upload className="dropzone-icon" />
              <p className="dropzone-title">Upload Answer Sheet</p>
              <p className="dropzone-subtitle">Drop an image or click to browse</p>
              <p className="dropzone-formats">JPG, PNG, WebP</p>
            </div>
          )}
          <input
            type="file"
            className="hidden-input"
            accept="image/jpeg,image/png,image/webp,image/jpg"
            onChange={handleFileChange}
          />
        </label>
      </div>

      {/* Question Input */}
      <div className="question-input-group">
        <div className="question-header">
          <FileText size={18} />
          <span>Question</span>
          <label className="auto-extract-toggle">
            <input
              type="checkbox"
              checked={autoExtract}
              onChange={(e) => setAutoExtract(e.target.checked)}
            />
            <span className="toggle-label">Auto-extract from image</span>
          </label>
        </div>
        <textarea
          className="question-textarea"
          placeholder={autoExtract
            ? "Question will be auto-extracted from the answer sheet..."
            : "Type the question the student is answering..."}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={autoExtract}
          rows={3}
        />
        
        <div className="marks-row">
          <label className="marks-label">
            Max Marks:
            <input
              type="number"
              className="marks-input"
              min={1}
              max={100}
              value={maxMarks}
              onChange={(e) => setMaxMarks(parseInt(e.target.value) || 10)}
            />
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <button
        className={`evaluate-btn ${loading ? 'evaluate-btn-loading' : ''}`}
        onClick={handleSubmit}
        disabled={loading || !file || (!question.trim() && !autoExtract)}
      >
        {loading ? (
          <>
            <svg className="spinner" viewBox="0 0 24 24">
              <circle className="spinner-track" cx="12" cy="12" r="10" />
              <path className="spinner-head" d="M4 12a8 8 0 018-8" />
            </svg>
            <span>Evaluating Pipeline...</span>
          </>
        ) : (
          <>
            <Sparkles size={18} />
            <span>Evaluate Answer</span>
          </>
        )}
      </button>
    </div>
  );
}
