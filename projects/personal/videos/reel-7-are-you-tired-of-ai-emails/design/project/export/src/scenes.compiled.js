// scenes.jsx - Scene components for the Enriquez OS reel

const BRAND = {
  bg: '#0A1628',
  bgDark: '#050B16',
  panel: '#0F1F36',
  panelHi: '#16294A',
  accent: '#4EB3F2',
  // primary blue (user tweak)
  accentDim: '#2A7FB8',
  dark: '#0772B1',
  teal: '#2D6A5E',
  orange: '#FF9A37',
  white: '#FFFFFF',
  offwhite: '#E8EEF5',
  grey: '#98A2B3',
  greyDim: '#4A5568',
  line: 'rgba(78, 179, 242, 0.18)',
  glow: 'rgba(78, 179, 242, 0.45)'
};
const MONO = "'Roboto Mono', ui-monospace, monospace";
const DISPLAY = "'Montserrat', system-ui, sans-serif";

// ── Shared chrome ──────────────────────────────────────────────────────────

function BackgroundGrid() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: `
        radial-gradient(ellipse 70% 50% at 50% 0%, rgba(78, 179, 242, 0.18), transparent 60%),
        radial-gradient(ellipse 50% 40% at 80% 100%, rgba(7, 114, 177, 0.22), transparent 60%),
        linear-gradient(180deg, ${BRAND.bg} 0%, ${BRAND.bgDark} 100%)
      `
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      backgroundImage: `
          linear-gradient(${BRAND.line} 1px, transparent 1px),
          linear-gradient(90deg, ${BRAND.line} 1px, transparent 1px)
        `,
      backgroundSize: '80px 80px',
      opacity: 0.35,
      maskImage: 'radial-gradient(ellipse 80% 60% at 50% 50%, black, transparent 90%)'
    }
  }));
}
function StepBadge({
  step,
  label,
  visible = true
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 60,
      left: 48,
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      opacity: visible ? 1 : 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 14,
      height: 14,
      borderRadius: '50%',
      background: BRAND.accent,
      boxShadow: `0 0 20px ${BRAND.glow}`
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 26,
      fontWeight: 500,
      color: BRAND.accent,
      letterSpacing: '0.15em'
    }
  }, "STEP ", step, " / 06"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 1,
      background: BRAND.line,
      marginLeft: 8,
      minWidth: 40
    }
  }));
}
function AELogo({
  size = 64,
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontWeight: 700,
      fontSize: size,
      color: BRAND.white,
      letterSpacing: '-0.04em',
      textShadow: `0 0 18px ${BRAND.glow}`,
      fontStyle: 'italic',
      ...style
    }
  }, "AE");
}
function Caption({
  children,
  y = 1640
}) {
  const {
    localTime,
    duration
  } = useSprite();
  const entryDur = 0.3;
  const exitDur = 0.3;
  const exitStart = Math.max(0, duration - exitDur);
  let opacity = 1;
  let ty = 0;
  if (localTime < entryDur) {
    const t = Easing.easeOutCubic(clamp(localTime / entryDur, 0, 1));
    opacity = t;
    ty = (1 - t) * 24;
  } else if (localTime > exitStart) {
    const t = Easing.easeInCubic(clamp((localTime - exitStart) / exitDur, 0, 1));
    opacity = 1 - t;
  }
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 48,
      right: 48,
      top: y,
      textAlign: 'center',
      fontFamily: DISPLAY,
      fontWeight: 300,
      fontSize: 54,
      lineHeight: 1.15,
      color: BRAND.white,
      letterSpacing: '-0.01em',
      opacity,
      transform: `translateY(${ty}px)`,
      textWrap: 'pretty'
    }
  }, children);
}
function Cursor({
  x,
  y,
  visible = true,
  label
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: y,
      opacity: visible ? 1 : 0,
      transition: 'opacity 200ms',
      pointerEvents: 'none',
      zIndex: 50
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "36",
    height: "44",
    viewBox: "0 0 36 44"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M4 4 L4 32 L12 26 L16 36 L21 34 L17 24 L28 24 Z",
    fill: "white",
    stroke: "#0A1628",
    strokeWidth: "2"
  })), label && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 30,
      top: 36,
      background: BRAND.accent,
      color: BRAND.bgDark,
      padding: '6px 12px',
      borderRadius: 6,
      fontFamily: MONO,
      fontWeight: 600,
      fontSize: 18,
      whiteSpace: 'nowrap',
      boxShadow: `0 0 24px ${BRAND.glow}`
    }
  }, label));
}

// ── Mock Email Client UI (original design, inspired by webmail layout) ─────

function MailClient({
  activeFolder = 'inbox',
  selectedRows = [],
  highlightFolder = false
}) {
  const folders = [{
    key: 'inbox',
    label: 'Inbox',
    count: 248
  }, {
    key: 'starred',
    label: 'Starred',
    count: 12
  }, {
    key: 'sent',
    label: 'Sent',
    count: 1024
  }, {
    key: 'drafts',
    label: 'Drafts',
    count: 3
  }, {
    key: 'archive',
    label: 'Archive',
    count: null
  }];
  const sentEmails = [{
    to: 'marcus@paragon.co',
    subj: 'Re: Q2 proposal — my take on scope',
    snip: 'Quick thought before we lock this in — I think we\'re…',
    time: 'Apr 18'
  }, {
    to: 'taylor@loom.co',
    subj: 'Following up on yesterday\'s call',
    snip: 'Hey Taylor, thanks again for making time. Here\'s where…',
    time: 'Apr 17'
  }, {
    to: 'jordan@northstar.io',
    subj: 'Intro — think you two should chat',
    snip: 'Jordan, meet Priya. Priya runs ops at Harbor and I think…',
    time: 'Apr 17'
  }, {
    to: 'priya@harborlabs.com',
    subj: 'Re: Onboarding thoughts',
    snip: 'Love this direction. One small nit on step 3 — the…',
    time: 'Apr 16'
  }, {
    to: 'team@enriquez.co',
    subj: 'Week recap + what\'s next',
    snip: 'Team — great week. Three wins worth calling out and…',
    time: 'Apr 15'
  }, {
    to: 'dev@klein.studio',
    subj: 'Re: Contract revisions',
    snip: 'All looks good to me. One thing I\'d flag before we sign…',
    time: 'Apr 14'
  }, {
    to: 'sam@vestal.co',
    subj: 'Re: Partnership idea',
    snip: 'Been chewing on this. Here\'s where I\'ve landed and…',
    time: 'Apr 13'
  }, {
    to: 'alex@mercury.build',
    subj: 'Quick ask — feedback on deck',
    snip: 'Alex, would love 5 min of your eyes on this before I…',
    time: 'Apr 12'
  }, {
    to: 'team@enriquez.co',
    subj: 'Heads up on Thursday\'s sync',
    snip: 'Moving our Thursday to 2pm so I can make it work with…',
    time: 'Apr 11'
  }, {
    to: 'chris@bellbrook.com',
    subj: 'Thanks for the intro',
    snip: 'Chris — really appreciate you putting us in touch. Reaching…',
    time: 'Apr 10'
  }];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 48,
      top: 180,
      width: 984,
      height: 1400,
      background: BRAND.bgDark,
      borderRadius: 24,
      border: `1px solid ${BRAND.line}`,
      boxShadow: `0 0 60px rgba(0,0,0,0.5), 0 0 40px ${BRAND.glow}`,
      overflow: 'hidden',
      display: 'flex',
      fontFamily: DISPLAY
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 280,
      background: BRAND.panel,
      padding: '28px 20px',
      borderRight: `1px solid ${BRAND.line}`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      marginBottom: 32,
      padding: '0 8px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      borderRadius: 8,
      background: BRAND.accent,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: MONO,
      fontWeight: 700,
      fontSize: 18,
      color: BRAND.bgDark,
      fontStyle: 'italic'
    }
  }, "AE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 16,
      color: BRAND.offwhite,
      letterSpacing: '0.1em',
      fontWeight: 500
    }
  }, "MAIL")), /*#__PURE__*/React.createElement("button", {
    style: {
      width: '100%',
      padding: '14px 16px',
      background: BRAND.accent,
      border: 'none',
      borderRadius: 10,
      color: BRAND.bgDark,
      fontFamily: DISPLAY,
      fontWeight: 600,
      fontSize: 18,
      marginBottom: 24,
      cursor: 'default',
      boxShadow: `0 0 20px ${BRAND.glow}`
    }
  }, "\uFF0B Compose"), folders.map(f => {
    const isActive = f.key === activeFolder;
    const isHighlighted = f.key === 'sent' && highlightFolder;
    return /*#__PURE__*/React.createElement("div", {
      key: f.key,
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px 14px',
        marginBottom: 4,
        borderRadius: 8,
        background: isHighlighted ? BRAND.accent : isActive ? 'rgba(78, 179, 242, 0.15)' : 'transparent',
        border: isHighlighted ? 'none' : `1px solid ${isActive ? BRAND.line : 'transparent'}`,
        boxShadow: isHighlighted ? `0 0 30px ${BRAND.glow}` : 'none',
        transition: 'all 200ms'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: DISPLAY,
        fontWeight: isActive || isHighlighted ? 500 : 300,
        fontSize: 18,
        color: isHighlighted ? BRAND.bgDark : isActive ? BRAND.accent : BRAND.offwhite
      }
    }, f.label), f.count != null && /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: MONO,
        fontSize: 14,
        color: isHighlighted ? BRAND.bgDark : BRAND.grey,
        fontWeight: isHighlighted ? 600 : 400
      }
    }, f.count));
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '24px 32px',
      borderBottom: `1px solid ${BRAND.line}`,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontWeight: 500,
      fontSize: 28,
      color: BRAND.white
    }
  }, "Sent"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 14,
      color: BRAND.grey,
      letterSpacing: '0.1em'
    }
  }, selectedRows.length > 0 ? `${selectedRows.length} SELECTED` : '1,024 MESSAGES')), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflow: 'hidden'
    }
  }, sentEmails.map((email, i) => {
    const isSelected = selectedRows.includes(i);
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        padding: '18px 28px',
        borderBottom: `1px solid rgba(78, 179, 242, 0.08)`,
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        background: isSelected ? 'rgba(78, 179, 242, 0.12)' : 'transparent',
        borderLeft: isSelected ? `3px solid ${BRAND.accent}` : '3px solid transparent',
        transition: 'all 150ms'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: 22,
        height: 22,
        borderRadius: 4,
        border: `2px solid ${isSelected ? BRAND.accent : BRAND.greyDim}`,
        background: isSelected ? BRAND.accent : 'transparent',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }
    }, isSelected && /*#__PURE__*/React.createElement("svg", {
      width: "14",
      height: "14",
      viewBox: "0 0 14 14"
    }, /*#__PURE__*/React.createElement("path", {
      d: "M2 7l3 3 7-7",
      stroke: BRAND.bgDark,
      strokeWidth: "2.5",
      fill: "none",
      strokeLinecap: "round",
      strokeLinejoin: "round"
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: MONO,
        fontSize: 14,
        color: BRAND.accent,
        fontWeight: 500,
        width: 220,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, email.to), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        overflow: 'hidden'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: DISPLAY,
        fontWeight: 500,
        fontSize: 17,
        color: BRAND.white,
        marginBottom: 3,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, email.subj), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: DISPLAY,
        fontWeight: 300,
        fontSize: 14,
        color: BRAND.grey,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap'
      }
    }, email.snip)), /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: MONO,
        fontSize: 13,
        color: BRAND.greyDim
      }
    }, email.time));
  }))));
}

// ── Mock AI Assistant UI ───────────────────────────────────────────────────

function AIAssistant({
  showProjectView = false,
  showSidebar = true,
  projectHighlighted = false,
  pastedContent = false,
  typedPrompt = '',
  sendingPrompt = false,
  showResponse = false,
  showInstructions = false,
  instructionsText = '',
  savedAsProject = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 48,
      top: 180,
      width: 984,
      height: 1400,
      background: BRAND.bgDark,
      borderRadius: 24,
      border: `1px solid ${BRAND.line}`,
      boxShadow: `0 0 60px rgba(0,0,0,0.5), 0 0 40px ${BRAND.glow}`,
      overflow: 'hidden',
      display: 'flex',
      fontFamily: DISPLAY
    }
  }, showSidebar && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 240,
      background: BRAND.panel,
      padding: '24px 16px',
      borderRight: `1px solid ${BRAND.line}`,
      display: 'flex',
      flexDirection: 'column',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 20,
      padding: '0 8px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: `radial-gradient(circle, ${BRAND.accent}, ${BRAND.dark})`,
      boxShadow: `0 0 12px ${BRAND.glow}`
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 13,
      color: BRAND.offwhite,
      letterSpacing: '0.12em',
      fontWeight: 500
    }
  }, "ASSISTANT")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 11,
      color: BRAND.greyDim,
      letterSpacing: '0.15em',
      padding: '4px 10px',
      marginTop: 8
    }
  }, "RECENT"), ['Draft investor update', 'Research: Q2 market', 'Rewrite cold outreach'].map((t, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      padding: '10px 12px',
      borderRadius: 8,
      fontFamily: DISPLAY,
      fontSize: 14,
      color: BRAND.grey,
      fontWeight: 300
    }
  }, t)), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 11,
      color: BRAND.greyDim,
      letterSpacing: '0.15em',
      padding: '4px 10px',
      marginTop: 16
    }
  }, "PROJECTS"), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '10px 12px',
      borderRadius: 8,
      background: projectHighlighted ? BRAND.accent : 'transparent',
      border: projectHighlighted ? 'none' : `1px solid ${BRAND.line}`,
      boxShadow: projectHighlighted ? `0 0 24px ${BRAND.glow}` : 'none',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      transition: 'all 200ms'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 14,
      height: 14,
      color: projectHighlighted ? BRAND.bgDark : BRAND.accent
    }
  }, /*#__PURE__*/React.createElement("svg", {
    viewBox: "0 0 14 14",
    width: "14",
    height: "14"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M1 4 L6 4 L7 5 L13 5 L13 12 L1 12 Z",
    fill: "currentColor",
    opacity: "0.9"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 14,
      color: projectHighlighted ? BRAND.bgDark : BRAND.white,
      fontWeight: savedAsProject ? 600 : 400
    }
  }, "My Voice"), savedAsProject && /*#__PURE__*/React.createElement("div", {
    style: {
      marginLeft: 'auto',
      fontFamily: MONO,
      fontSize: 10,
      color: projectHighlighted ? BRAND.bgDark : BRAND.accent,
      letterSpacing: '0.1em'
    }
  }, "NEW"))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: BRAND.bgDark
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px 32px',
      borderBottom: `1px solid ${BRAND.line}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontWeight: 500,
      fontSize: 22,
      color: BRAND.white
    }
  }, showProjectView ? 'My Voice' : 'New chat'), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: BRAND.greyDim
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: BRAND.greyDim
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 10,
      height: 10,
      borderRadius: '50%',
      background: BRAND.greyDim
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      padding: '28px 32px',
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
      overflow: 'hidden'
    }
  }, showInstructions ? /*#__PURE__*/React.createElement(ProjectInstructions, {
    text: instructionsText
  }) : /*#__PURE__*/React.createElement(React.Fragment, null, pastedContent && /*#__PURE__*/React.createElement(UserBubble, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 13,
      color: BRAND.grey,
      marginBottom: 10,
      letterSpacing: '0.1em'
    }
  }, "\u2500\u2500 10 EMAILS PASTED \u2500\u2500"), ['Quick thought before we lock this in — I think we\'re...', 'Hey Taylor, thanks again for making time. Here\'s where...', 'Jordan, meet Priya. Priya runs ops at Harbor and I think...', 'Love this direction. One small nit on step 3 — the...', 'Team — great week. Three wins worth calling out and...'].map((line, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      fontFamily: DISPLAY,
      fontSize: 14,
      color: BRAND.offwhite,
      fontWeight: 300,
      lineHeight: 1.5,
      paddingLeft: 10,
      borderLeft: `2px solid ${BRAND.accentDim}`,
      marginBottom: 8
    }
  }, line)), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      color: BRAND.greyDim,
      marginTop: 8,
      fontStyle: 'italic'
    }
  }, "+ 5 more emails")), typedPrompt && /*#__PURE__*/React.createElement(UserBubble, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 17,
      color: BRAND.white,
      fontWeight: 400,
      lineHeight: 1.5,
      whiteSpace: 'pre-wrap'
    }
  }, typedPrompt)), showResponse && /*#__PURE__*/React.createElement(AIBubble, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 15,
      color: BRAND.offwhite,
      fontWeight: 300,
      lineHeight: 1.55
    }
  }, "Got it. I've analyzed your 10 emails. Here's what defines your voice:"), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 12
    }
  }), [{
    k: 'Tone',
    v: 'warm, direct, slightly informal'
  }, {
    k: 'Openers',
    v: 'name + quick context, no "Hi, hope you\'re well"'
  }, {
    k: 'Rhythm',
    v: 'short sentences. em-dashes for asides.'
  }, {
    k: 'Sign-off',
    v: '"—Allen" (lowercase, no formal closer)'
  }].map((row, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      gap: 12,
      padding: '6px 0',
      borderBottom: i < 3 ? `1px dashed ${BRAND.line}` : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      color: BRAND.accent,
      width: 80,
      letterSpacing: '0.1em',
      paddingTop: 2
    }
  }, row.k.toUpperCase()), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 14,
      color: BRAND.white,
      flex: 1,
      fontWeight: 300
    }
  }, row.v)))))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px 32px 28px',
      borderTop: `1px solid ${BRAND.line}`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: BRAND.panel,
      border: `1px solid ${sendingPrompt ? BRAND.accent : BRAND.line}`,
      boxShadow: sendingPrompt ? `0 0 24px ${BRAND.glow}` : 'none',
      borderRadius: 14,
      padding: '16px 18px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      transition: 'all 200ms'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      fontFamily: DISPLAY,
      fontSize: 16,
      color: BRAND.grey,
      fontWeight: 300
    }
  }, "Message your assistant..."), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 36,
      height: 36,
      borderRadius: 8,
      background: BRAND.accent,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: `0 0 12px ${BRAND.glow}`
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "16",
    height: "16",
    viewBox: "0 0 16 16"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M8 14 L8 2 M3 7 L8 2 L13 7",
    stroke: BRAND.bgDark,
    strokeWidth: "2.5",
    fill: "none",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  })))))));
}
function UserBubble({
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      alignSelf: 'flex-end',
      maxWidth: '82%',
      background: BRAND.panelHi,
      border: `1px solid ${BRAND.line}`,
      borderRadius: 14,
      padding: '16px 20px'
    }
  }, children);
}
function AIBubble({
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      alignSelf: 'flex-start',
      maxWidth: '88%',
      display: 'flex',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: `radial-gradient(circle, ${BRAND.accent}, ${BRAND.dark})`,
      flexShrink: 0,
      boxShadow: `0 0 10px ${BRAND.glow}`
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      background: 'rgba(78, 179, 242, 0.06)',
      border: `1px solid ${BRAND.line}`,
      borderRadius: 14,
      padding: '16px 20px'
    }
  }, children));
}
function ProjectInstructions({
  text
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: BRAND.panel,
      border: `1px solid ${BRAND.line}`,
      borderRadius: 14,
      padding: '24px 26px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 16
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 18,
      height: 18,
      borderRadius: 4,
      background: BRAND.accent,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("svg", {
    width: "12",
    height: "12",
    viewBox: "0 0 12 12"
  }, /*#__PURE__*/React.createElement("path", {
    d: "M2 6 L5 9 L10 3",
    stroke: BRAND.bgDark,
    strokeWidth: "2",
    fill: "none",
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 13,
      color: BRAND.accent,
      letterSpacing: '0.15em',
      fontWeight: 500
    }
  }, "PROJECT INSTRUCTIONS")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 15,
      color: BRAND.offwhite,
      lineHeight: 1.65,
      fontWeight: 400,
      whiteSpace: 'pre-wrap',
      minHeight: 400
    }
  }, text, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-block',
      width: 10,
      height: 18,
      background: BRAND.accent,
      marginLeft: 2,
      verticalAlign: 'text-bottom',
      animation: 'aeblink 800ms steps(2) infinite'
    }
  })));
}

// ── Helper: typewriter effect based on progress ────────────────────────────

function typeOut(fullText, progress) {
  const n = Math.floor(fullText.length * clamp(progress, 0, 1));
  return fullText.slice(0, n);
}

// ────────────────────────────────────────────────────────────────────────────
// SCENES (timeline mapped to the 15.0s–55.0s range, 0s–40s local)
// ────────────────────────────────────────────────────────────────────────────

// STEP 1 — 0:00 → 0:03 — "Open your email sent folder"
function Step1_OpenSent() {
  const {
    localTime
  } = useSprite();
  // Cursor animates from floating to the Sent folder
  const cursorX = interpolate([0, 1.2, 2.2], [720, 240, 220], Easing.easeInOutCubic)(localTime);
  const cursorY = interpolate([0, 1.2, 2.2], [900, 540, 540], Easing.easeInOutCubic)(localTime);
  const highlight = localTime > 1.6;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "01",
    label: "OPEN SENT"
  }), /*#__PURE__*/React.createElement(MailClient, {
    activeFolder: highlight ? 'sent' : 'inbox',
    highlightFolder: highlight
  }), /*#__PURE__*/React.createElement(Cursor, {
    x: cursorX,
    y: cursorY,
    label: localTime > 1.8 ? 'Sent' : null
  }), /*#__PURE__*/React.createElement(Caption, null, "Open your email sent folder."));
}

// STEP 2 — 0:03 → 0:09 — "Copy your last 10 emails"
function Step2_CopyEmails() {
  const {
    localTime
  } = useSprite();
  // Select 10 rows one by one
  const selected = [];
  const rowCount = Math.min(10, Math.floor(localTime / 0.35));
  for (let i = 0; i < rowCount; i++) selected.push(i);

  // Cursor bounces down the list
  const cursorY = 280 + Math.min(rowCount, 9) * 90;
  const cursorX = 180 + Math.sin(localTime * 3) * 6;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "02",
    label: "COPY 10 EMAILS"
  }), /*#__PURE__*/React.createElement(MailClient, {
    activeFolder: "sent",
    selectedRows: selected
  }), /*#__PURE__*/React.createElement(Cursor, {
    x: cursorX,
    y: Math.min(cursorY, 1540),
    label: rowCount >= 10 ? 'Copy — 10 selected' : `${rowCount} / 10`
  }), /*#__PURE__*/React.createElement(Caption, null, "Copy your last 10 emails \u2014 the ones written in your voice."));
}

// STEP 3 — 0:09 → 0:14 — "Paste into ChatGPT"
function Step3_Paste() {
  const {
    localTime
  } = useSprite();
  const showPaste = localTime > 0.8;
  const sending = localTime > 2.0 && localTime < 2.8;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "03",
    label: "PASTE INTO AI"
  }), /*#__PURE__*/React.createElement(AIAssistant, {
    pastedContent: showPaste,
    sendingPrompt: sending
  }), /*#__PURE__*/React.createElement(Caption, null, "Paste them into your AI assistant."));
}

// STEP 4 — 0:14 → 0:27 — "Write this prompt"
function Step4_Prompt() {
  const {
    localTime
  } = useSprite();
  const fullPrompt = "Study how I write. Break down the components so you can learn my voice.\n\n" + "Save it as a template so we match this tone every time.\n\n" + "Ask clarifying questions if you need to.";

  // Typewriter runs from 0.3s to 10s
  const typeProgress = clamp((localTime - 0.3) / 9.0, 0, 1);
  const typed = typeOut(fullPrompt, typeProgress);
  const showResp = localTime > 11.0;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "04",
    label: "THE PROMPT"
  }), /*#__PURE__*/React.createElement(AIAssistant, {
    pastedContent: true,
    typedPrompt: typed,
    sendingPrompt: localTime > 10.5 && localTime < 11.5,
    showResponse: showResp
  }), /*#__PURE__*/React.createElement(Caption, {
    y: 1660
  }, localTime < 5.5 ? "\"Study how I write.\"" : localTime < 9.0 ? "\"Save it as a template.\"" : "\"Ask clarifying questions.\""));
}

// STEP 5 — 0:27 → 0:32 — "Save as a project"
function Step5_SaveProject() {
  const {
    localTime
  } = useSprite();
  const highlight = localTime > 1.2;
  const saved = localTime > 2.5;
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "05",
    label: "SAVE AS PROJECT"
  }), /*#__PURE__*/React.createElement(AIAssistant, {
    pastedContent: true,
    showResponse: true,
    projectHighlighted: highlight,
    savedAsProject: saved
  }), /*#__PURE__*/React.createElement(Cursor, {
    x: 180,
    y: 920,
    label: saved ? 'Saved ✓' : 'Save as project'
  }), /*#__PURE__*/React.createElement(Caption, null, "Save it as a project."));
}

// STEP 6 — 0:32 → 0:40 — "Paste the prompt into project instructions"
function Step6_PasteInstructions() {
  const {
    localTime
  } = useSprite();
  const fullInstructions = "# MY VOICE — TEMPLATE\n\n" + "TONE: warm, direct, lightly informal.\n" + "OPENERS: name + quick context. Never \"Hope you're well.\"\n" + "RHYTHM: short sentences. em-dashes for asides.\n" + "SIGN-OFF: —Allen (lowercase, no formal closer)\n\n" + "RULES:\n" + "  · Don't use corporate filler.\n" + "  · Don't use exclamation points.\n" + "  · Ask clarifying questions when needed.\n" + "  · Match this tone for every email.";
  const typeProgress = clamp((localTime - 0.5) / 6.0, 0, 1);
  const typed = typeOut(fullInstructions, typeProgress);
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "06",
    label: "PROJECT INSTRUCTIONS"
  }), /*#__PURE__*/React.createElement(AIAssistant, {
    showSidebar: true,
    showProjectView: true,
    savedAsProject: true,
    showInstructions: true,
    instructionsText: typed
  }), /*#__PURE__*/React.createElement(Caption, {
    y: 1700
  }, "Paste your prompt into the project instructions."));
}

// STEP 7 / FINALE — "Now every email sounds like you — not a machine"
function FinaleEmail() {
  const {
    localTime,
    duration
  } = useSprite();
  const body = "Marcus —\n\n" + "Quick thought before we lock this in. I think we're close but the scope is still fuzzy on section 3.\n\n" + "Can we trim it to just the onboarding flow? Easier to ship, easier to measure.\n\n" + "Happy to jump on a 10 if that's faster.\n\n" + "—Allen";
  const typeProgress = clamp((localTime - 0.4) / 4.2, 0, 1);
  const typed = typeOut(body, typeProgress);

  // Stamp appears near the end
  const stampIn = localTime > 4.8;
  const stampT = clamp((localTime - 4.8) / 0.6, 0, 1);
  const stampScale = 0.6 + 0.4 * Easing.easeOutBack(stampT);
  const stampRotate = -8 + 4 * (1 - stampT);
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(StepBadge, {
    step: "\u2713",
    label: "RESULT"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 48,
      top: 180,
      width: 984,
      height: 1400,
      background: BRAND.bgDark,
      borderRadius: 24,
      border: `1px solid ${BRAND.line}`,
      boxShadow: `0 0 60px rgba(0,0,0,0.5), 0 0 60px ${BRAND.glow}`,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: DISPLAY
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px 28px',
      borderBottom: `1px solid ${BRAND.line}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 34,
      height: 34,
      borderRadius: 8,
      background: BRAND.accent,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: MONO,
      fontWeight: 700,
      fontSize: 16,
      color: BRAND.bgDark,
      fontStyle: 'italic'
    }
  }, "AE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontWeight: 500,
      fontSize: 22,
      color: BRAND.white
    }
  }, "New message")), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      color: BRAND.accent,
      letterSpacing: '0.15em',
      padding: '6px 10px',
      border: `1px solid ${BRAND.line}`,
      borderRadius: 20
    }
  }, "MY VOICE \xB7 ON")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px 28px',
      borderBottom: `1px solid ${BRAND.line}`
    }
  }, [{
    l: 'To',
    v: 'marcus@paragon.co'
  }, {
    l: 'Subject',
    v: 'Re: Q2 proposal — my take on scope'
  }].map((f, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'flex',
      gap: 16,
      padding: '10px 0',
      borderBottom: i === 0 ? `1px dashed ${BRAND.line}` : 'none'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 13,
      color: BRAND.grey,
      letterSpacing: '0.1em',
      width: 80,
      paddingTop: 2
    }
  }, f.l.toUpperCase()), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 17,
      color: BRAND.white,
      fontWeight: 400,
      flex: 1
    }
  }, f.v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      padding: '28px 32px',
      fontFamily: DISPLAY,
      fontSize: 20,
      color: BRAND.white,
      fontWeight: 300,
      lineHeight: 1.55,
      whiteSpace: 'pre-wrap',
      position: 'relative'
    }
  }, typed, typeProgress < 1 && /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-block',
      width: 10,
      height: 22,
      background: BRAND.accent,
      marginLeft: 2,
      verticalAlign: 'text-bottom',
      animation: 'aeblink 800ms steps(2) infinite'
    }
  }), stampIn && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      right: 40,
      bottom: 40,
      transform: `rotate(${stampRotate}deg) scale(${stampScale})`,
      padding: '18px 28px',
      border: `4px solid ${BRAND.accent}`,
      borderRadius: 12,
      fontFamily: MONO,
      fontWeight: 700,
      fontSize: 28,
      color: BRAND.accent,
      letterSpacing: '0.1em',
      textAlign: 'center',
      lineHeight: 1.15,
      boxShadow: `0 0 40px ${BRAND.glow}`,
      background: 'rgba(5, 11, 22, 0.6)',
      backdropFilter: 'blur(4px)'
    }
  }, "SOUNDS", /*#__PURE__*/React.createElement("br", null), "LIKE YOU", /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      fontWeight: 500,
      letterSpacing: '0.25em',
      color: BRAND.offwhite,
      marginTop: 8
    }
  }, "NOT A MACHINE"))), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '18px 28px',
      borderTop: `1px solid ${BRAND.line}`,
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      background: BRAND.accent,
      border: 'none',
      borderRadius: 999,
      padding: '12px 28px',
      fontFamily: MONO,
      fontSize: 15,
      fontWeight: 600,
      color: BRAND.bgDark,
      letterSpacing: '0.1em',
      boxShadow: `0 0 20px ${BRAND.glow}`
    }
  }, "SEND \u2713"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      color: BRAND.grey,
      letterSpacing: '0.1em'
    }
  }, "DRAFTED IN 4s \xB7 AE VOICE MATCH 97%"))), /*#__PURE__*/React.createElement(Caption, {
    y: 1660
  }, "Now every email sounds like you \u2014 not a machine."));
}

// ── Intro and outro transitions ────────────────────────────────────────────

function StepTransition({
  step,
  title
}) {
  const {
    localTime,
    duration,
    progress
  } = useSprite();

  // Slide-in card from below, scales up
  const entryT = Easing.easeOutCubic(clamp(localTime / 0.35, 0, 1));
  const exitStart = duration - 0.3;
  const exitT = localTime > exitStart ? Easing.easeInCubic((localTime - exitStart) / 0.3) : 0;
  const opacity = entryT * (1 - exitT);
  const ty = (1 - entryT) * 60 + exitT * -30;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'rgba(5, 11, 22, 0.82)',
      backdropFilter: 'blur(20px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      opacity
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      transform: `translateY(${ty}px)`
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 36,
      color: BRAND.accent,
      letterSpacing: '0.3em',
      fontWeight: 500,
      marginBottom: 24,
      textShadow: `0 0 20px ${BRAND.glow}`
    }
  }, "STEP ", step), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: DISPLAY,
      fontSize: 110,
      fontWeight: 300,
      color: BRAND.white,
      lineHeight: 1.05,
      letterSpacing: '-0.02em',
      maxWidth: 900,
      margin: '0 auto',
      textWrap: 'balance'
    }
  }, title)));
}

// ── Export ─────────────────────────────────────────────────────────────────

Object.assign(window, {
  BRAND,
  MONO,
  DISPLAY,
  BackgroundGrid,
  StepBadge,
  AELogo,
  Caption,
  Cursor,
  MailClient,
  AIAssistant,
  Step1_OpenSent,
  Step2_CopyEmails,
  Step3_Paste,
  Step4_Prompt,
  Step5_SaveProject,
  Step6_PasteInstructions,
  FinaleEmail,
  StepTransition
});