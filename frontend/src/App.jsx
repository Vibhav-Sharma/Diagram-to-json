import React, { useState } from 'react';
import { UploadCloud, Image as ImageIcon, Code2, AlertCircle } from 'lucide-react';

function App() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Analysis failed');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-8">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Multimodal Diagram Analyzer</h1>
        <p className="text-gray-600">Upload a hand-drawn diagram to extract structure, labels, and connections.</p>
      </header>

      <div className="w-full max-w-6xl bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 flex flex-col">
        {/* Upload Section */}
        <div className="p-8 border-b border-gray-100 flex flex-col items-center">
          <label className="flex flex-col items-center justify-center w-full max-w-2xl h-48 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <UploadCloud className="w-10 h-10 text-gray-400 mb-3" />
              <p className="mb-2 text-sm text-gray-500 font-semibold">Click to upload or drag and drop</p>
              <p className="text-xs text-gray-500">SVG, PNG, JPG or GIF</p>
            </div>
            <input type="file" className="hidden" accept="image/*" onChange={handleFileChange} />
          </label>

          {previewUrl && (
            <button
              onClick={handleUpload}
              disabled={loading}
              className={`mt-6 px-8 py-3 rounded-lg font-semibold text-white transition-all ${
                loading ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 shadow-md hover:shadow-lg'
              }`}
            >
              {loading ? 'Analyzing with Gemini...' : 'Analyze Diagram'}
            </button>
          )}

          {error && (
            <div className="mt-6 flex items-center text-red-600 bg-red-50 px-4 py-3 rounded-lg w-full max-w-2xl border border-red-100">
              <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0" />
              <p className="text-sm font-medium">{error}</p>
            </div>
          )}
        </div>

        {/* Results Section */}
        {(previewUrl || result) && (
          <div className="p-8 bg-gray-50 grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: Original Image */}
            <div className="flex flex-col">
              <div className="flex items-center mb-3 text-gray-700">
                <ImageIcon className="w-5 h-5 mr-2" />
                <h3 className="font-semibold">Original Image</h3>
              </div>
              <div className="flex-1 bg-white border border-gray-200 rounded-xl overflow-hidden flex items-center justify-center p-2 min-h-[300px]">
                <img src={previewUrl} alt="Original" className="max-w-full max-h-[500px] object-contain rounded-lg shadow-sm" />
              </div>
            </div>

            {/* Right: Visualization Image */}
            <div className="flex flex-col">
              <div className="flex items-center mb-3 text-indigo-700">
                <ImageIcon className="w-5 h-5 mr-2 text-indigo-600" />
                <h3 className="font-semibold text-indigo-900">AI Structural Visualization</h3>
              </div>
              <div className="flex-1 bg-white border border-indigo-100 rounded-xl overflow-hidden flex items-center justify-center p-2 shadow-inner min-h-[300px]">
                {loading ? (
                  <div className="flex flex-col items-center text-indigo-400">
                    <svg className="animate-spin h-10 w-10 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p className="text-sm font-medium animate-pulse">Extracting structure and geometry...</p>
                  </div>
                ) : result?.visualization_image ? (
                  <img src={result.visualization_image} alt="Visualization" className="max-w-full max-h-[500px] object-contain rounded-lg shadow-sm" />
                ) : (
                  <div className="text-gray-400 text-sm text-center px-6">
                    Run analysis to see the AI's structural interpretation highlighted here.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Bottom: JSON Data */}
        {result?.diagram_json && (
          <div className="p-8 border-t border-gray-100">
            <div className="flex items-center mb-4 text-gray-700">
              <Code2 className="w-5 h-5 mr-2" />
              <h3 className="font-semibold">Extracted Semantic JSON</h3>
            </div>
            <div className="bg-gray-900 rounded-xl p-6 overflow-x-auto shadow-inner">
              <pre className="text-green-400 text-sm font-mono leading-relaxed">
                {JSON.stringify(result.diagram_json, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
