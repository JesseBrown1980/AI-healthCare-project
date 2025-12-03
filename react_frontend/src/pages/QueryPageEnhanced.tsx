/**
 * Enhanced Medical Query Page
 * RAG-powered medical question answering with reasoning and citations
 */

import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { queryMedical, submitFeedback } from '../api';
import type { QueryResult, QuerySource } from '../api/types';
import { useQueryStore } from '../store';
import { useNotification } from '../hooks';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Input,
  Badge,
  Spinner,
  EmptyState,
} from '../components/ui';
import './QueryPageEnhanced.css';

// ============================================================================
// Query Page Component
// ============================================================================

const QueryPageEnhanced: React.FC = () => {
  const [searchParams] = useSearchParams();
  const patientIdParam = searchParams.get('patientId');

  // State
  const [question, setQuestion] = useState('');
  const [patientId, setPatientId] = useState(patientIdParam ?? '');
  const [includeReasoning, setIncludeReasoning] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResult | null>(null);

  // Store
  const { queryHistory, addToHistory, updateFeedback } = useQueryStore();
  const { success, error: notifyError } = useNotification();

  // Refs
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // ============================================================================
  // Handlers
  // ============================================================================

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) {
      notifyError('Empty Question', 'Please enter a medical question');
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const queryResult = await queryMedical(question.trim(), {
        patientId: patientId || undefined,
        includeReasoning,
      });

      setResult(queryResult);

      // Add to history
      addToHistory({
        question: question.trim(),
        answer: queryResult.answer ?? '',
        reasoning: Array.isArray(queryResult.reasoning)
          ? queryResult.reasoning
          : queryResult.reasoning
          ? [queryResult.reasoning]
          : undefined,
        sources: queryResult.sources as any,
        confidence: queryResult.confidence,
        patientId: patientId || undefined,
      });

      success('Query Complete', 'Your question has been answered');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Query failed';
      notifyError('Query Error', message);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (type: 'positive' | 'negative') => {
    if (!result?.query_id) return;

    try {
      await submitFeedback(result.query_id, type);
      updateFeedback(result.query_id, type);
      success('Feedback Submitted', 'Thank you for your feedback!');
    } catch (err) {
      notifyError('Feedback Error', 'Unable to submit feedback');
    }
  };

  const handleHistoryClick = (item: typeof queryHistory[0]) => {
    setQuestion(item.question);
    if (item.patientId) {
      setPatientId(item.patientId);
    }
  };

  const handleClear = () => {
    setQuestion('');
    setResult(null);
    inputRef.current?.focus();
  };

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="query-page">
      {/* Header */}
      <header className="query-page__header">
        <h1 className="query-page__title">Medical Query Assistant</h1>
        <p className="query-page__subtitle">
          Ask clinical questions and receive AI-powered answers with evidence-based reasoning
        </p>
      </header>

      <div className="query-page__content">
        {/* Main Query Area */}
        <div className="query-page__main">
          {/* Query Form */}
          <Card className="query-form">
            <CardContent>
              <form onSubmit={handleSubmit}>
                <div className="query-form__input-group">
                  <Input
                    ref={inputRef}
                    placeholder="Ask a medical question... (e.g., 'What are the contraindications for metformin?')"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    disabled={loading}
                  />
                  <Button type="submit" loading={loading} disabled={loading || !question.trim()}>
                    {loading ? 'Thinking...' : 'Ask'}
                  </Button>
                </div>

                <div className="query-form__options">
                  <div className="query-form__option">
                    <Input
                      placeholder="Patient ID (optional)"
                      value={patientId}
                      onChange={(e) => setPatientId(e.target.value)}
                      disabled={loading}
                    />
                  </div>
                  <label className="query-form__checkbox">
                    <input
                      type="checkbox"
                      checked={includeReasoning}
                      onChange={(e) => setIncludeReasoning(e.target.checked)}
                      disabled={loading}
                    />
                    Include step-by-step reasoning
                  </label>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Loading State */}
          {loading && (
            <Card className="query-loading">
              <CardContent>
                <div className="query-loading__content">
                  <Spinner size="lg" />
                  <p>Analyzing your question...</p>
                  <p className="query-loading__hint">
                    Searching medical knowledge bases and generating a comprehensive response
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Result */}
          {result && !loading && (
            <div className="query-result">
              {/* Question */}
              <Card className="query-result__question">
                <CardContent>
                  <div className="query-result__question-header">
                    <span className="query-result__label">Your Question</span>
                    {result.confidence !== undefined && (
                      <Badge variant={result.confidence >= 0.8 ? 'success' : result.confidence >= 0.5 ? 'warning' : 'default'}>
                        {Math.round(result.confidence * 100)}% confidence
                      </Badge>
                    )}
                  </div>
                  <p className="query-result__question-text">{result.question}</p>
                </CardContent>
              </Card>

              {/* Answer */}
              <Card className="query-result__answer">
                <CardHeader>
                  <CardTitle>Answer</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="query-result__answer-text">
                    {result.answer ?? 'No answer available.'}
                  </div>

                  {/* Feedback */}
                  <div className="query-result__feedback">
                    <span>Was this answer helpful?</span>
                    <Button variant="ghost" size="sm" onClick={() => handleFeedback('positive')}>
                      👍 Yes
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleFeedback('negative')}>
                      👎 No
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Reasoning */}
              {result.reasoning && (
                <Card className="query-result__reasoning">
                  <CardHeader>
                    <CardTitle>Step-by-Step Reasoning</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ol className="reasoning-list">
                      {(Array.isArray(result.reasoning) ? result.reasoning : [result.reasoning]).map(
                        (step, index) => (
                          <li key={index} className="reasoning-list__item">
                            <span className="reasoning-list__number">{index + 1}</span>
                            <span className="reasoning-list__text">{step}</span>
                          </li>
                        )
                      )}
                    </ol>
                  </CardContent>
                </Card>
              )}

              {/* Sources */}
              {result.sources && (result.sources as any[]).length > 0 && (
                <Card className="query-result__sources">
                  <CardHeader>
                    <CardTitle>Sources & References</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="sources-list">
                      {(result.sources as any[]).map((source: QuerySource, index: number) => (
                        <div key={index} className="source-item">
                          <div className="source-item__header">
                            <Badge variant="info" size="sm">
                              {source.source_type ?? 'Reference'}
                            </Badge>
                            {source.relevance_score !== undefined && (
                              <span className="source-item__relevance">
                                {Math.round(source.relevance_score * 100)}% relevant
                              </span>
                            )}
                          </div>
                          <h4 className="source-item__title">
                            {source.url ? (
                              <a href={source.url} target="_blank" rel="noopener noreferrer">
                                {source.title ?? source.url}
                              </a>
                            ) : (
                              source.title ?? `Source ${index + 1}`
                            )}
                          </h4>
                          {source.snippet && (
                            <p className="source-item__snippet">{source.snippet}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Actions */}
              <div className="query-result__actions">
                <Button variant="outline" onClick={handleClear}>
                  Ask Another Question
                </Button>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!result && !loading && (
            <Card className="query-empty">
              <CardContent>
                <EmptyState
                  icon={<span style={{ fontSize: '3rem' }}>🔬</span>}
                  title="Ask a Medical Question"
                  description="Enter a clinical question above to receive an AI-powered answer with evidence-based reasoning and citations."
                />

                {/* Example Questions */}
                <div className="example-questions">
                  <h4>Example Questions:</h4>
                  <div className="example-questions__list">
                    {[
                      'What are the first-line treatments for Type 2 Diabetes?',
                      'What are the contraindications for ACE inhibitors?',
                      'How should warfarin be monitored in elderly patients?',
                      'What are the symptoms of acute myocardial infarction?',
                    ].map((q, i) => (
                      <button
                        key={i}
                        className="example-question"
                        onClick={() => setQuestion(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar - Query History */}
        <aside className="query-page__sidebar">
          <Card>
            <CardHeader>
              <CardTitle>Recent Queries</CardTitle>
            </CardHeader>
            <CardContent>
              {queryHistory.length === 0 ? (
                <p className="query-history__empty">No recent queries</p>
              ) : (
                <div className="query-history">
                  {queryHistory.slice(0, 10).map((item) => (
                    <button
                      key={item.id}
                      className="query-history__item"
                      onClick={() => handleHistoryClick(item)}
                    >
                      <span className="query-history__question">{item.question}</span>
                      <span className="query-history__time">
                        {formatRelativeTime(item.timestamp)}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
};

// ============================================================================
// Helper Functions
// ============================================================================

function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diffMs = now - timestamp;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

export default QueryPageEnhanced;
