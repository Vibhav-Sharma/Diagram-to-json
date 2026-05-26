import React from 'react';

export default function ScoreGauge({ score, maxScore, theoryScore, maxTheory, diagramBonus, maxBonus }) {
  const percentage = Math.round((score / maxScore) * 100);
  
  // Color based on percentage
  let gaugeColor = '#ef4444'; // red
  if (percentage >= 80) gaugeColor = '#22c55e'; // green
  else if (percentage >= 60) gaugeColor = '#3b82f6'; // blue
  else if (percentage >= 40) gaugeColor = '#f59e0b'; // amber
  else if (percentage >= 20) gaugeColor = '#f97316'; // orange

  // SVG arc calculation
  const radius = 80;
  const circumference = Math.PI * radius; // half-circle
  const offset = circumference - (percentage / 100) * circumference;

  return (
    <div className="score-gauge">
      <div className="gauge-visual">
        <svg viewBox="0 0 200 120" className="gauge-svg">
          {/* Background arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="rgba(255,255,255,0.1)"
            strokeWidth="12"
            strokeLinecap="round"
          />
          {/* Filled arc */}
          <path
            d="M 20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={gaugeColor}
            strokeWidth="12"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="gauge-fill"
          />
        </svg>
        <div className="gauge-value">
          <span className="gauge-number" style={{ color: gaugeColor }}>{score}</span>
          <span className="gauge-max">/ {maxScore}</span>
        </div>
      </div>

      <div className="score-breakdown">
        <div className="breakdown-item">
          <span className="breakdown-label">Theory Answer</span>
          <div className="breakdown-bar-wrapper">
            <div
              className="breakdown-bar theory-bar"
              style={{ width: `${(theoryScore / maxTheory) * 100}%` }}
            />
          </div>
          <span className="breakdown-value">{theoryScore}/{maxTheory}</span>
        </div>
        
        <div className="breakdown-item">
          <span className="breakdown-label">Diagram Bonus</span>
          <div className="breakdown-bar-wrapper">
            <div
              className="breakdown-bar bonus-bar"
              style={{ width: `${maxBonus > 0 ? (diagramBonus / maxBonus) * 100 : 0}%` }}
            />
          </div>
          <span className="breakdown-value">+{diagramBonus}/{maxBonus}</span>
        </div>
      </div>
    </div>
  );
}
