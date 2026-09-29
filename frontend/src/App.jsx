import React, { useState } from 'react'
import { 
  Sparkles, 
  Database, 
  Send, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  HelpCircle, 
  Code, 
  Table as TableIcon, 
  Copy, 
  Check, 
  Bot, 
  User, 
  ShieldCheck,
  MessageSquare
} from 'lucide-react'

const SUGGESTED_QUERIES = [
  "Which products generated the most revenue?",
  "Who was our best customer last month?",
  "Show me sales for last month.",
  "Which products have stock below 40 units?",
  "What is the capital of France? (Test Unrelated)"
]

export default function App() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [copied, setCopied] = useState(false)

  // Interactive Clarification State
  const [pendingClarification, setPendingClarification] = useState(null)
  const [userClarificationAnswer, setUserClarificationAnswer] = useState('')
  const [clarificationHistory, setClarificationHistory] = useState([])

  const executeQuery = async (queryText, history = []) => {
    setLoading(true)
    setError(null)

    try {
      const apiUrl = window.location.port === '5173' ? '/api/query' : 'http://127.0.0.1:8000/query'
      
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: queryText,
          clarification_history: history
        }),
      })

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`)
      }

      const data = await response.json()

      if (data.needs_clarification && data.clarifying_question) {
        // Agent is asking the user a clarifying question!
        setPendingClarification(data.clarifying_question)
        setResult(null)
      } else {
        // Completed pipeline (either success or terminal error)
        setPendingClarification(null)
        setResult(data)
      }
    } catch (err) {
      console.error(err)
      setError(err.message || 'Failed to connect to Text2SQL backend')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (q = question) => {
    const queryText = q.trim()
    if (!queryText || loading) return

    setResult(null)
    setPendingClarification(null)
    setClarificationHistory([])
    setUserClarificationAnswer('')
    
    executeQuery(queryText, [])
  }

  const handleClarificationSubmit = (e) => {
    e.preventDefault()
    if (!userClarificationAnswer.trim() || !pendingClarification || loading) return

    const updatedHistory = [
      ...clarificationHistory,
      {
        agent_question: pendingClarification,
        user_answer: userClarificationAnswer.trim()
      }
    ]

    setClarificationHistory(updatedHistory)
    setUserClarificationAnswer('')
    setPendingClarification(null)

    // Re-invoke with clarification context
    executeQuery(question, updatedHistory)
  }

  const handleCopySql = () => {
    if (!result?.sql_query) return
    navigator.clipboard.writeText(result.sql_query)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-indigo-500 selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Database className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-semibold text-base text-slate-100">Text2SQL Agent</h1>
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  LangGraph Multi-Agent
                </span>
              </div>
              <p className="text-xs text-slate-400">Natural Language to PostgreSQL with Interactive Clarification</p>
            </div>
          </div>

          <div className="hidden sm:flex items-center gap-3 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Groq (openai/gpt-oss-120b)
            </span>
            <span>•</span>
            <span>PostgreSQL 16</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl w-full mx-auto px-4 py-8 flex-1 flex flex-col gap-6">
        
        {/* Search Input Box */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg focus-within:border-indigo-500/60 transition-colors">
          <form 
            onSubmit={(e) => {
              e.preventDefault()
              handleSubmit()
            }}
            className="flex gap-2 items-center"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about the e-commerce database (e.g. products, sales, customers)..."
              disabled={loading}
              className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm shadow-indigo-500/20"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <span>Run Agent</span>
                  <Send className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </form>

          {/* Quick Suggestions */}
          <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-500 font-medium">Try asking:</span>
            {SUGGESTED_QUERIES.map((q, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setQuestion(q)
                  handleSubmit(q)
                }}
                disabled={loading}
                className="text-xs bg-slate-800/70 hover:bg-slate-800 text-slate-300 hover:text-white px-2.5 py-1 rounded-md border border-slate-700/50 transition-colors disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Loading Spinner State */}
        {loading && (
          <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-8 flex flex-col items-center justify-center text-center gap-3">
            <div className="relative">
              <div className="h-10 w-10 rounded-full border-2 border-indigo-500/20 border-t-indigo-500 animate-spin"></div>
              <Sparkles className="h-4 w-4 text-indigo-400 absolute inset-0 m-auto" />
            </div>
            <p className="text-sm text-slate-300 font-medium">Multi-Agent Workflow in Progress</p>
            <p className="text-xs text-slate-500 max-w-sm">
              Checking intent &rarr; validating ambiguity &rarr; generating & executing SQL
            </p>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-4 flex items-start gap-3 text-rose-300 text-sm">
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-rose-200">Execution Error</p>
              <p className="text-xs text-rose-300/90 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* INTERACTIVE CLARIFICATION CARD (When Agent needs user answer) */}
        {pendingClarification && !loading && (
          <div className="bg-slate-900 border-2 border-indigo-500/60 rounded-xl p-5 shadow-xl animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2">
              <MessageSquare className="h-4 w-4" />
              <span>Clarification Required by Agent</span>
            </div>

            <p className="text-sm text-slate-100 font-medium mb-4 bg-slate-950/70 p-3.5 rounded-lg border border-slate-800/80 flex items-start gap-2.5">
              <Bot className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <span>{pendingClarification}</span>
            </p>

            <form onSubmit={handleClarificationSubmit} className="flex gap-2">
              <input
                type="text"
                autoFocus
                value={userClarificationAnswer}
                onChange={(e) => setUserClarificationAnswer(e.target.value)}
                placeholder="Type your answer (e.g. 'Highest revenue', 'Total quantity', etc.)..."
                className="flex-1 bg-slate-950 border border-slate-700 focus:border-indigo-500 px-3.5 py-2 text-sm text-slate-100 placeholder:text-slate-500 rounded-lg outline-none"
              />
              <button
                type="submit"
                disabled={!userClarificationAnswer.trim()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm shadow-indigo-500/20"
              >
                Submit Answer
              </button>
            </form>
          </div>
        )}

        {/* System Error Message from Backend (Unrelated, Unsafe, or Retries Exhausted) */}
        {result?.error_message && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3 text-amber-300 text-sm">
            <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-amber-200">Notice</p>
              <p className="text-xs text-amber-300/90 mt-0.5">{result.error_message}</p>
            </div>
          </div>
        )}

        {/* Results Container */}
        {result && (
          <div className="flex flex-col gap-5 animate-in fade-in duration-300">
            
            {/* 1. Clarification Dialogue History (if any occurred) */}
            {result.clarification_history && result.clarification_history.length > 0 && (
              <div className="bg-slate-900 border border-indigo-900/40 rounded-xl p-4 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                  <HelpCircle className="h-4 w-4" />
                  <span>Ambiguity Clarification History</span>
                </div>
                
                <div className="space-y-2.5">
                  {result.clarification_history.map((turn, i) => (
                    <div key={i} className="space-y-1.5 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <div className="flex items-start gap-2 text-indigo-300">
                        <Bot className="h-3.5 w-3.5 mt-0.5 shrink-0 text-indigo-400" />
                        <div><strong className="font-semibold text-slate-200">Agent asked:</strong> {turn.agent_question}</div>
                      </div>
                      <div className="flex items-start gap-2 text-slate-300 pl-5">
                        <User className="h-3.5 w-3.5 mt-0.5 shrink-0 text-slate-400" />
                        <div><strong className="font-semibold text-slate-200">You answered:</strong> {turn.user_answer}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. Final Plain-English Answer */}
            {result.final_answer && (
              <div className="bg-slate-900 border border-emerald-900/40 rounded-xl p-5 shadow-sm">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Natural Language Answer</span>
                </div>
                <p className="text-slate-100 text-sm leading-relaxed font-normal">
                  {result.final_answer}
                </p>
              </div>
            )}

            {/* 3. Generated SQL Query */}
            {result.sql_query && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                    <Code className="h-4 w-4 text-indigo-400" />
                    <span>Generated PostgreSQL Query</span>
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <ShieldCheck className="h-3 w-3" /> Validated
                    </span>
                  </div>
                  <button
                    onClick={handleCopySql}
                    className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/40 transition-colors"
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-4 text-xs font-mono text-indigo-200 bg-slate-950/70 overflow-x-auto leading-relaxed">
                  {result.sql_query}
                </pre>
              </div>
            )}

            {/* 4. Query Results Table */}
            {result.query_result && result.query_result.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="px-4 py-2.5 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
                    <TableIcon className="h-4 w-4 text-indigo-400" />
                    <span>Query Output ({result.query_result.length} row{result.query_result.length > 1 ? 's' : ''})</span>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-72">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/90 text-slate-400 uppercase tracking-wider sticky top-0 border-b border-slate-800">
                      <tr>
                        {Object.keys(result.query_result[0]).map((col) => (
                          <th key={col} className="px-4 py-2.5 font-medium whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                      {result.query_result.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                          {Object.values(row).map((val, colIdx) => (
                            <td key={colIdx} className="px-4 py-2 whitespace-nowrap">
                              {val === null || val === undefined ? (
                                <span className="text-slate-600 italic">null</span>
                              ) : typeof val === 'number' ? (
                                Number.isInteger(val) ? val : Number(val).toFixed(2)
                              ) : (
                                String(val)
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Empty result set notice */}
            {result.query_result && result.query_result.length === 0 && !result.error_message && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-4 text-center text-xs text-slate-400">
                Query executed successfully, but returned 0 rows from the database.
              </div>
            )}

          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-4 text-center text-xs text-slate-600">
        Built with LangGraph, Groq, PostgreSQL & FastAPI
      </footer>
    </div>
  )
}
