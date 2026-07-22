import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import {
  Dumbbell, Zap, Brain, TrendingUp, Heart,
  Shield, Send, Loader2, Flame, ChevronRight,
  Sparkles, Activity, BarChart3, MessageSquare,
  Target, Clock, Users, Star, AlertTriangle,
  CheckCircle2, Circle, Info, Cpu
} from 'lucide-react'
import './App.css'

// ─── API base URL ────────────────────────────────────────────────────────────
// In production (Vercel), VITE_API_BASE_URL = https://forgeai-d0gl.onrender.com
// In local dev, it is empty — Vite's proxy forwards /api → localhost:5001
const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

// ─── Agent registry ─────────────────────────────────────────────────────────
const AGENTS = {
  workout_planner:    { label: 'Workout Planner',    short: 'Workout',     icon: Dumbbell,    hue: '24'   },
  nutrition_agent:    { label: 'Nutrition Agent',    short: 'Nutrition',   icon: Flame,       hue: '142'  },
  progress_analyst:   { label: 'Progress Analyst',  short: 'Progress',    icon: TrendingUp,  hue: '234'  },
  motivational_coach: { label: 'Motivational Coach',short: 'Mindset',     icon: Heart,       hue: '330'  },
  recovery_agent:     { label: 'Recovery Specialist',short: 'Recovery',   icon: Shield,      hue: '186'  },
  supervisor:         { label: 'AI Supervisor',      short: 'Routing',     icon: Brain,       hue: '270'  },
  unknown:            { label: 'ForgeAI',            short: 'AI',          icon: Zap,         hue: '24'   },
}

const QUICK_PROMPTS = [
  { text: 'Design me a chest & triceps workout', icon: Dumbbell, tag: 'Workout' },
  { text: 'What should I eat for muscle building?', icon: Flame, tag: 'Nutrition' },
  { text: 'Am I overtraining? I feel drained', icon: Shield, tag: 'Recovery' },
  { text: "I've lost motivation — help me get it back", icon: Heart, tag: 'Mindset' },
  { text: 'Check my progressive overload progress', icon: TrendingUp, tag: 'Progress' },
  { text: 'Calculate my TDEE and macros', icon: Target, tag: 'Nutrition' },
]

// ─── Typing animation ────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="typing-wrap">
      <div className="typing-avatar">
        <Zap size={13} />
      </div>
      <div className="typing-bubble">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </div>
    </div>
  )
}

// ─── Agent pill / badge ──────────────────────────────────────────────────────
function AgentPill({ agentKey, size = 'sm' }) {
  const agent = AGENTS[agentKey] || AGENTS.unknown
  const Icon  = agent.icon
  return (
    <span className={`agent-pill agent-pill-${size}`} data-hue={agent.hue}
      style={{ '--h': agent.hue }}>
      <Icon size={size === 'sm' ? 10 : 13} />
      {agent.short}
    </span>
  )
}

// ─── Recovery flag banner ────────────────────────────────────────────────────
function RecoveryBanner({ flag }) {
  if (!flag || flag === 'safe') return null
  const isBlocked = flag === 'blocked'
  return (
    <div className={`recovery-banner ${flag}`}>
      {isBlocked ? <AlertTriangle size={14} /> : <Info size={14} />}
      <span>{isBlocked ? 'Plan flagged — review before attempting' : 'Recovery note attached'}</span>
    </div>
  )
}

// ─── Single message ──────────────────────────────────────────────────────────
function Message({ msg, isLatest }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`msg-row ${isUser ? 'msg-user' : 'msg-ai'} ${isLatest ? 'msg-latest' : ''}`}>
      {!isUser && (
        <div className="msg-avatar ai-av" style={{ '--h': (AGENTS[msg.agent] || AGENTS.unknown).hue }}>
          {(() => { const Icon = (AGENTS[msg.agent] || AGENTS.unknown).icon; return <Icon size={14} /> })()}
        </div>
      )}

      <div className="msg-body">
        {!isUser && (
          <div className="msg-meta">
            <AgentPill agentKey={msg.agent} size="sm" />
            <span className="msg-time">{msg.time}</span>
          </div>
        )}

        <div className={`msg-bubble ${isUser ? 'bubble-user' : 'bubble-ai'}`}>
          {isUser ? (
            <p>{msg.text}</p>
          ) : (
            <ReactMarkdown
              components={{
                h1: ({ children }) => <h1 className="md-h1">{children}</h1>,
                h2: ({ children }) => <h2 className="md-h2">{children}</h2>,
                h3: ({ children }) => <h3 className="md-h3">{children}</h3>,
                strong: ({ children }) => <strong className="md-bold">{children}</strong>,
                code: ({ inline, children }) => inline
                  ? <code className="md-inline-code">{children}</code>
                  : <pre className="md-code-block"><code>{children}</code></pre>,
                li: ({ children }) => <li className="md-li">{children}</li>,
                hr: () => <hr className="md-hr" />,
              }}
            >
              {msg.text}
            </ReactMarkdown>
          )}
        </div>

        {!isUser && <RecoveryBanner flag={msg.recoveryFlag} />}

        {isUser && <span className="msg-time" style={{ alignSelf: 'flex-end' }}>{msg.time}</span>}

        {!isUser && msg.toolsUsed?.length > 0 && (
          <div className="tools-used">
            <Cpu size={10} />
            {msg.toolsUsed.map(t => <span key={t} className="tool-tag">{t.replace('tool_', '')}</span>)}
          </div>
        )}
      </div>

      {isUser && (
        <div className="msg-avatar user-av">U</div>
      )}
    </div>
  )
}

// ─── Agent activity feed ─────────────────────────────────────────────────────
function AgentFeed({ log }) {
  if (log.length === 0) {
    return (
      <div className="feed-empty">
        <div className="feed-empty-icon"><Brain size={28} /></div>
        <p>Send a message to watch your AI team coordinate</p>
      </div>
    )
  }

  return (
    <div className="feed-list">
      {log.map((item, i) => {
        const agent = AGENTS[item.agent] || AGENTS.unknown
        const Icon  = agent.icon
        const isDone = item.status === 'done'
        return (
          <div key={i} className={`feed-item ${isDone ? 'feed-done' : 'feed-active'}`}>
            <div className="feed-icon" style={{ '--h': agent.hue }}>
              <Icon size={12} />
            </div>
            <div className="feed-info">
              <span className="feed-agent">{agent.label}</span>
              <span className="feed-detail">{item.detail}</span>
            </div>
            <div className="feed-status">
              {isDone
                ? <CheckCircle2 size={14} className="icon-done" />
                : <Circle size={14} className="icon-active spin-slow" />
              }
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Stats panel ────────────────────────────────────────────────────────────
function StatsPanel({ metrics }) {
  const items = [
    { label: 'Messages sent',  value: metrics.messages,   icon: MessageSquare, hue: '24'  },
    { label: 'Agents invoked', value: metrics.agents,     icon: Users,         hue: '234' },
    { label: 'Tools called',   value: metrics.tools,      icon: Cpu,           hue: '142' },
    { label: 'Session time',   value: metrics.time,       icon: Clock,         hue: '270' },
  ]

  return (
    <div className="stats-container">
      <div className="stats-header">
        <BarChart3 size={16} />
        <h2>Session Overview</h2>
      </div>
      <div className="stats-grid">
        {items.map(item => {
          const Icon = item.icon
          return (
            <div key={item.label} className="stat-card" style={{ '--h': item.hue }}>
              <div className="stat-icon"><Icon size={16} /></div>
              <span className="stat-value">{item.value}</span>
              <span className="stat-label">{item.label}</span>
            </div>
          )
        })}
      </div>

      <div className="agents-grid-header">
        <Star size={14} />
        <h3>Your Coaching Team</h3>
      </div>
      <div className="agents-team-grid">
        {Object.entries(AGENTS)
          .filter(([k]) => !['supervisor', 'unknown'].includes(k))
          .map(([key, agent]) => {
            const Icon = agent.icon
            return (
              <div key={key} className="team-card" style={{ '--h': agent.hue }}>
                <div className="team-icon"><Icon size={18} /></div>
                <span className="team-label">{agent.label}</span>
                <div className="team-dot" />
              </div>
            )
          })
        }
      </div>
    </div>
  )
}

// ─── Sidebar ─────────────────────────────────────────────────────────────────
function Sidebar({ active, setActive, feedCount }) {
  const nav = [
    { id: 'chat',    icon: MessageSquare, label: 'Chat'    },
    { id: 'agents',  icon: Activity,      label: 'Agents', badge: feedCount },
    { id: 'stats',   icon: BarChart3,     label: 'Stats'   },
  ]

  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div className="sb-logo">
          <Flame size={18} />
        </div>
        <div>
          <span className="sb-name">ForgeAI</span>
          <span className="sb-tagline">Multi-Agent Coaching</span>
        </div>
      </div>

      <nav className="sb-nav">
        {nav.map(({ id, icon: Icon, label, badge }) => (
          <button
            key={id}
            className={`sb-link ${active === id ? 'sb-active' : ''}`}
            onClick={() => setActive(id)}
          >
            <Icon size={16} />
            <span>{label}</span>
            {badge > 0 && <span className="sb-badge">{badge}</span>}
          </button>
        ))}
      </nav>

      <div className="sb-agents">
        <p className="sb-section">Live Agents</p>
        {Object.entries(AGENTS)
          .filter(([k]) => !['supervisor', 'unknown'].includes(k))
          .map(([key, agent]) => {
            const Icon = agent.icon
            return (
              <div key={key} className="sb-agent" style={{ '--h': agent.hue }}>
                <div className="sb-agent-icon"><Icon size={12} /></div>
                <span className="sb-agent-name">{agent.label}</span>
                <span className="sb-agent-dot" />
              </div>
            )
          })}
      </div>
    </aside>
  )
}

// ─── Root App ────────────────────────────────────────────────────────────────
export default function App() {
  const [sessionId, setSessionId]   = useState(null)
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [activePanel, setActivePanel] = useState('chat')
  const [feed, setFeed]             = useState([])
  const [connected, setConnected]   = useState(false)
  const [sessionMetrics, setSessionMetrics] = useState({
    messages: 0, agents: 0, tools: 0, time: '0:00'
  })
  const [startTime]                 = useState(Date.now())

  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const inputWrap = useRef(null)

  const ts = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // ── Auto-scroll ────────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // ── Session timer ──────────────────────────────────────────────────────────
  useEffect(() => {
    const timer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      const m = Math.floor(elapsed / 60)
      const s = elapsed % 60
      setSessionMetrics(prev => ({ ...prev, time: `${m}:${s.toString().padStart(2, '0')}` }))
    }, 1000)
    return () => clearInterval(timer)
  }, [startTime])

  // ── Init session ───────────────────────────────────────────────────────────
  useEffect(() => {
    axios.post(`${API_BASE}/api/chat/start`)
      .then(res => {
        setSessionId(res.data.session_id)
        setConnected(true)
        setMessages([{
          id: 'welcome',
          role: 'assistant',
          text: "Hey, welcome to **ForgeAI** 🔥\n\nI've got a full team ready for you — a workout planner, nutritionist, progress analyst, recovery specialist, and mindset coach. They work together to give you one coherent answer.\n\nWhat are we working on?",
          agent: null,
          time: ts(),
        }])
      })
      .catch(() => {
        setMessages([{
          id: 'err',
          role: 'assistant',
          text: '**Backend not running.** Start the Flask server on port 5001:\n\n```\ncd ForgeAI && python -m backend.app\n```',
          agent: null,
          time: ts(),
        }])
      })
  }, [])

  // ── Auto-resize textarea ───────────────────────────────────────────────────
  const autoResize = (e) => {
    e.target.style.height = 'auto'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  // ── Send message ───────────────────────────────────────────────────────────
  const send = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || !sessionId || loading) return

    setInput('')
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
    setLoading(true)
    setActivePanel('chat')

    const userMsg = { id: Date.now(), role: 'user', text: msg, time: ts() }
    setMessages(prev => [...prev, userMsg])
    setFeed(prev => [{ agent: 'supervisor', detail: 'Analysing request…', status: 'active', time: ts() }, ...prev])

    try {
      const res = await axios.post(`${API_BASE}/api/chat/send`, { session_id: sessionId, message: msg })
      const { response, agent_used, agents_used = [], tools_used = [], recovery_flag, routes = [] } = res.data

      // Update feed
      setFeed(prev => {
        const next = [
          { agent: 'supervisor', detail: `Routed → ${routes.join(', ') || agent_used}`, status: 'done', time: ts() },
          ...agents_used.map(a => ({ agent: a, detail: 'Response generated', status: 'done', time: ts() })),
          ...prev.slice(1)
        ]
        return next.slice(0, 30)
      })

      const aiMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        text: response,
        agent: agent_used,
        toolsUsed: tools_used,
        recoveryFlag: recovery_flag,
        time: ts(),
      }
      setMessages(prev => [...prev, aiMsg])

      // Update session metrics
      setSessionMetrics(prev => ({
        ...prev,
        messages: prev.messages + 1,
        agents:   prev.agents + (agents_used.length || 1),
        tools:    prev.tools + tools_used.length,
      }))
    } catch (err) {
      const isRateLimit = err.response?.status === 429
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: isRateLimit
          ? '⏳ **Rate limit reached.** You can send up to 10 messages per minute. Give it a moment.'
          : '**Something went wrong.** The backend may have timed out. Try again.',
        agent: null,
        time: ts(),
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 80)
    }
  }, [input, sessionId, loading])

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const showQuickPrompts = messages.length <= 1 && !loading

  return (
    <div className="shell">
      <Sidebar active={activePanel} setActive={setActivePanel} feedCount={feed.length} />

      <main className="main">

        {/* ── Top bar ───────────────────────────────────────────────────── */}
        <header className="topbar">
          <div className="topbar-left">
            <div className={`status-dot ${connected ? 'online' : 'offline'}`} />
            <span className="status-label">{connected ? 'All agents online' : 'Connecting…'}</span>
          </div>
          <div className="topbar-agents">
            {Object.entries(AGENTS)
              .filter(([k]) => !['supervisor', 'unknown'].includes(k))
              .map(([key, a]) => {
                const Icon = a.icon
                return (
                  <div key={key} title={a.label} className="topbar-agent" style={{ '--h': a.hue }}>
                    <Icon size={11} />
                  </div>
                )
              })}
          </div>
        </header>

        {/* ── Panel area ────────────────────────────────────────────────── */}
        <div className="panels">

          {/* Chat */}
          <div className={`panel ${activePanel === 'chat' ? 'panel-show' : 'panel-hide'}`}>
            <div className="messages">
              {messages.map((m, i) => (
                <Message key={m.id} msg={m} isLatest={i === messages.length - 1} />
              ))}
              {loading && <TypingIndicator />}
              <div ref={bottomRef} />
            </div>

            {/* Quick prompts */}
            {showQuickPrompts && (
              <div className="quick-area">
                <p className="quick-label">Suggested questions</p>
                <div className="quick-grid">
                  {QUICK_PROMPTS.map(({ text, icon: Icon, tag }) => (
                    <button key={text} className="quick-card" onClick={() => send(text)}>
                      <div className="quick-icon"><Icon size={14} /></div>
                      <div className="quick-body">
                        <span className="quick-tag">{tag}</span>
                        <span className="quick-text">{text}</span>
                      </div>
                      <ChevronRight size={13} className="quick-arrow" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="input-dock" ref={inputWrap}>
              <div className={`input-box ${loading ? 'input-loading' : ''}`}>
                <textarea
                  ref={inputRef}
                  className="input-ta"
                  value={input}
                  onChange={e => { setInput(e.target.value); autoResize(e) }}
                  onKeyDown={onKey}
                  placeholder="Ask your coaching team anything…"
                  disabled={loading || !connected}
                  rows={1}
                />
                <button
                  className={`send-btn ${!input.trim() || loading ? 'send-off' : 'send-on'}`}
                  onClick={() => send()}
                  disabled={!input.trim() || loading || !connected}
                  aria-label="Send message"
                >
                  {loading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
                </button>
              </div>
              <p className="input-hint">
                <kbd>Enter</kbd> to send &nbsp;·&nbsp; <kbd>Shift+Enter</kbd> for new line
              </p>
            </div>
          </div>

          {/* Agent feed */}
          <div className={`panel panel-pad ${activePanel === 'agents' ? 'panel-show' : 'panel-hide'}`}>
            <div className="panel-title">
              <Activity size={16} />
              <h2>Agent Activity</h2>
              <span className="panel-subtitle">Live coordination feed</span>
            </div>
            <AgentFeed log={feed} />
          </div>

          {/* Stats */}
          <div className={`panel panel-pad ${activePanel === 'stats' ? 'panel-show' : 'panel-hide'}`}>
            <StatsPanel metrics={sessionMetrics} />
          </div>
        </div>
      </main>
    </div>
  )
}
