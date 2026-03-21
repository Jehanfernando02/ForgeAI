import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import {
  Dumbbell, Zap, Brain, TrendingUp, Heart,
  Shield, Send, Loader2, Flame, ChevronRight,
  Sparkles, Activity, BarChart3, MessageSquare
} from 'lucide-react'
import './App.css'

// ── Agent metadata ──────────────────────────────────────────
const AGENTS = {
  workout_planner:    { label: 'Workout Planner',    icon: Dumbbell,    color: '#f97316', bg: 'rgba(249,115,22,0.12)'  },
  nutrition_agent:    { label: 'Nutrition Agent',     icon: Flame,       color: '#22c55e', bg: 'rgba(34,197,94,0.12)'   },
  progress_analyst:   { label: 'Progress Analyst',   icon: TrendingUp,  color: '#6366f1', bg: 'rgba(99,102,241,0.12)'  },
  motivational_coach: { label: 'Motivational Coach', icon: Heart,       color: '#ec4899', bg: 'rgba(236,72,153,0.12)'  },
  recovery_agent:     { label: 'Recovery Agent',     icon: Shield,      color: '#22d3ee', bg: 'rgba(34,211,238,0.12)'  },
  supervisor:         { label: 'Supervisor',         icon: Brain,       color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)'  },
}

const QUICK_PROMPTS = [
  { text: 'Design me a chest & triceps workout', icon: Dumbbell },
  { text: 'Calculate my macro targets', icon: Flame },
  { text: 'Am I overtraining?', icon: Activity },
  { text: 'I feel unmotivated lately', icon: Heart },
]

// ── Typing indicator ────────────────────────────────────────
function TypingDots() {
  return (
    <div className="typing-dots">
      <span /><span /><span />
    </div>
  )
}

// ── Agent badge ──────────────────────────────────────────────
function AgentBadge({ agentKey }) {
  const agent = AGENTS[agentKey]
  if (!agent) return null
  const Icon = agent.icon
  return (
    <div className="agent-badge" style={{ background: agent.bg, borderColor: agent.color + '40' }}>
      <Icon size={11} style={{ color: agent.color }} />
      <span style={{ color: agent.color }}>{agent.label}</span>
    </div>
  )
}

// ── Single message bubble ────────────────────────────────────
function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && (
        <div className="avatar assistant-avatar">
          <Zap size={14} />
        </div>
      )}
      <div className="message-content">
        {!isUser && msg.agent && <AgentBadge agentKey={msg.agent} />}
        <div className={`bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
          {isUser ? (
            <p>{msg.text}</p>
          ) : (
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          )}
        </div>
        <span className="timestamp">{msg.time}</span>
      </div>
      {isUser && (
        <div className="avatar user-avatar">
          <span>U</span>
        </div>
      )}
    </div>
  )
}

// ── Activity panel item ──────────────────────────────────────
function ActivityItem({ item }) {
  const agent = AGENTS[item.agent]
  if (!agent) return null
  const Icon = agent.icon
  return (
    <div className={`activity-item ${item.status}`}>
      <div className="activity-icon" style={{ background: agent.bg }}>
        <Icon size={13} style={{ color: agent.color }} />
      </div>
      <div className="activity-info">
        <span className="activity-agent" style={{ color: agent.color }}>
          {agent.label}
        </span>
        <span className="activity-detail">{item.detail}</span>
      </div>
      <div className={`activity-status-dot ${item.status}`} />
    </div>
  )
}

// ── Sidebar ──────────────────────────────────────────────────
function Sidebar({ activePanel, setActivePanel, activityLog }) {
  const navItems = [
    { id: 'chat',     icon: MessageSquare, label: 'Chat'      },
    { id: 'activity', icon: Activity,      label: 'Agents'    },
    { id: 'stats',    icon: BarChart3,     label: 'Stats'     },
  ]
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon"><Flame size={20} /></div>
        <div className="logo-text">
          <span className="logo-name">ForgeAI</span>
          <span className="logo-sub">AI Coaching</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            className={`nav-btn ${activePanel === id ? 'active' : ''}`}
            onClick={() => setActivePanel(id)}
          >
            <Icon size={18} />
            <span>{label}</span>
            {id === 'activity' && activityLog.length > 0 && (
              <span className="nav-badge">{activityLog.length}</span>
            )}
          </button>
        ))}
      </nav>

      <div className="sidebar-agents">
        <p className="sidebar-section-label">Your Team</p>
        {Object.entries(AGENTS).filter(([k]) => k !== 'supervisor').map(([key, agent]) => {
          const Icon = agent.icon
          return (
            <div key={key} className="sidebar-agent">
              <div className="sidebar-agent-icon" style={{ background: agent.bg }}>
                <Icon size={13} style={{ color: agent.color }} />
              </div>
              <span className="sidebar-agent-name">{agent.label}</span>
            </div>
          )
        })}
      </div>
    </aside>
  )
}

// ── Stats panel placeholder ──────────────────────────────────
function StatsPanel() {
  const stats = [
    { label: 'Workouts Logged', value: '0', color: '#f97316' },
    { label: 'Avg Daily Protein', value: '— g', color: '#22c55e' },
    { label: 'Streak', value: '0 days', color: '#6366f1' },
    { label: 'PRs This Month', value: '0', color: '#22d3ee' },
  ]
  return (
    <div className="stats-panel">
      <div className="panel-header">
        <BarChart3 size={18} style={{ color: '#f97316' }} />
        <h2>Your Progress</h2>
      </div>
      <div className="stats-grid">
        {stats.map(s => (
          <div key={s.label} className="stat-card">
            <span className="stat-value" style={{ color: s.color }}>{s.value}</span>
            <span className="stat-label">{s.label}</span>
          </div>
        ))}
      </div>
      <div className="coming-soon">
        <Sparkles size={32} style={{ color: '#f97316', opacity: 0.5 }} />
        <p>Full analytics dashboard coming in Phase 8</p>
        <span>Workout trends, strength curves, macro adherence & more</span>
      </div>
    </div>
  )
}

// ── Activity panel ───────────────────────────────────────────
function ActivityPanel({ log }) {
  return (
    <div className="activity-panel">
      <div className="panel-header">
        <Activity size={18} style={{ color: '#f97316' }} />
        <h2>Agent Activity</h2>
      </div>
      {log.length === 0 ? (
        <div className="activity-empty">
          <Brain size={36} style={{ color: '#f97316', opacity: 0.3 }} />
          <p>No activity yet</p>
          <span>Send a message to see your AI team in action</span>
        </div>
      ) : (
        <div className="activity-list">
          {log.map((item, i) => <ActivityItem key={i} item={item} />)}
        </div>
      )}
    </div>
  )
}

// ── Main App ─────────────────────────────────────────────────
export default function App() {
  const [sessionId, setSessionId]   = useState(null)
  const [messages, setMessages]     = useState([])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [activePanel, setActivePanel] = useState('chat')
  const [activityLog, setActivityLog] = useState([])
  const [connected, setConnected]   = useState(false)

  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Initialize session
  useEffect(() => {
    axios.post('/api/chat/start').then(res => {
      setSessionId(res.data.session_id)
      setConnected(true)
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        text: "Welcome to **ForgeAI** 🔥\n\nI'm your AI coaching team — a workout planner, nutritionist, progress analyst, recovery specialist, and motivational coach all working together.\n\nWhat are we working on today?",
        agent: null,
        time: now()
      }])
    }).catch(() => {
      setMessages([{
        id: 'error',
        role: 'assistant',
        text: 'Failed to connect to ForgeAI. Make sure the backend is running on port 5001.',
        agent: null,
        time: now()
      }])
    })
  }, [])

  const addActivity = useCallback((agent, detail, status = 'active') => {
    setActivityLog(prev => [{ agent, detail, status, time: now() }, ...prev].slice(0, 20))
  }, [])

  const sendMessage = useCallback(async (text) => {
    const messageText = text || input.trim()
    if (!messageText || !sessionId || loading) return

    setInput('')
    setLoading(true)
    setActivePanel('chat')

    // Add user message
    setMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      text: messageText,
      time: now()
    }])

    // Show supervisor activity
    addActivity('supervisor', 'Routing your request...', 'active')

    try {
      const res = await axios.post('/api/chat/send', {
        session_id: sessionId,
        message: messageText
      })

      const { response, agent_used, routing, routes } = res.data

      // Update activity log
      addActivity('supervisor', `Routed → ${routes?.join(', ') || agent_used}`, 'done')
      addActivity(agent_used, 'Generating response...', 'done')

      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: response,
        agent: agent_used,
        routing,
        time: now()
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: 'Something went wrong. Please try again.',
        agent: null,
        time: now()
      }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [input, sessionId, loading, addActivity])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="app-shell">
      <Sidebar
        activePanel={activePanel}
        setActivePanel={setActivePanel}
        activityLog={activityLog}
      />

      <main className="main-area">
        {/* Top bar */}
        <header className="topbar">
          <div className="topbar-left">
            <div className={`connection-dot ${connected ? 'online' : 'offline'}`} />
            <span className="topbar-status">
              {connected ? 'All agents online' : 'Connecting...'}
            </span>
          </div>
          <div className="topbar-right">
            {Object.entries(AGENTS).slice(0, 5).map(([key, agent]) => {
              const Icon = agent.icon
              return (
                <div key={key} className="topbar-agent" title={agent.label}
                  style={{ background: agent.bg, borderColor: agent.color + '30' }}>
                  <Icon size={12} style={{ color: agent.color }} />
                </div>
              )
            })}
          </div>
        </header>

        {/* Panels */}
        <div className="panel-area">
          {/* Chat panel */}
          <div className={`panel chat-panel ${activePanel === 'chat' ? 'panel-visible' : 'panel-hidden'}`}>
            <div className="messages-area">
              {messages.map(msg => <Message key={msg.id} msg={msg} />)}
              {loading && (
                <div className="message-row assistant">
                  <div className="avatar assistant-avatar"><Zap size={14} /></div>
                  <div className="message-content">
                    <div className="bubble bubble-assistant loading-bubble">
                      <TypingDots />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Quick prompts */}
            {messages.length <= 1 && (
              <div className="quick-prompts">
                {QUICK_PROMPTS.map(({ text, icon: Icon }) => (
                  <button key={text} className="quick-btn" onClick={() => sendMessage(text)}>
                    <Icon size={14} />
                    <span>{text}</span>
                    <ChevronRight size={12} className="quick-arrow" />
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="input-area">
              <div className="input-wrapper">
                <textarea
                  ref={inputRef}
                  className="chat-input"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Ask your coaching team anything..."
                  disabled={loading || !connected}
                  rows={1}
                />
                <button
                  className={`send-btn ${loading || !input.trim() ? 'disabled' : ''}`}
                  onClick={() => sendMessage()}
                  disabled={loading || !input.trim() || !connected}
                >
                  {loading
                    ? <Loader2 size={18} className="spin" />
                    : <Send size={18} />
                  }
                </button>
              </div>
              <p className="input-hint">
                Press <kbd>Enter</kbd> to send · <kbd>Shift+Enter</kbd> for new line
              </p>
            </div>
          </div>

          {/* Activity panel */}
          <div className={`panel ${activePanel === 'activity' ? 'panel-visible' : 'panel-hidden'}`}>
            <ActivityPanel log={activityLog} />
          </div>

          {/* Stats panel */}
          <div className={`panel ${activePanel === 'stats' ? 'panel-visible' : 'panel-hidden'}`}>
            <StatsPanel />
          </div>
        </div>
      </main>
    </div>
  )
}
