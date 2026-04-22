/*EDITMODE-BEGIN*/
const TWEAKS = {
  "accent": "#4EB3F2",
  "showTransitions": true,
  "showProgressBar": true
};
/*EDITMODE-END*/

// Segment boundaries (local seconds from the 15.0s mark of the script)
// 0–3:    Step 1 — Open sent folder
// 3–9:    Step 2 — Copy 10 emails
// 9–14:   Step 3 — Paste into AI
// 14–27:  Step 4 — Write this prompt (incl. 3 sub-lines)
// 27–32:  Step 5 — Save as project
// 32–40:  Step 6 — Paste into project instructions

const DURATION = 42;
function ProgressBar() {
  if (!TWEAKS.showProgressBar) return null;
  const {
    time
  } = useTimeline();
  const pct = time / DURATION * 100;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 28,
      left: 48,
      right: 48,
      height: 6,
      borderRadius: 3,
      background: 'rgba(255,255,255,0.08)',
      overflow: 'hidden',
      zIndex: 100
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${pct}%`,
      height: '100%',
      background: BRAND.accent,
      boxShadow: `0 0 12px ${BRAND.glow}`,
      transition: 'none'
    }
  }));
}
function Watermark() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 28,
      right: 48,
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      zIndex: 100,
      opacity: 0.8
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 18,
      fontWeight: 700,
      color: BRAND.accent,
      fontStyle: 'italic',
      letterSpacing: '-0.02em',
      textShadow: `0 0 12px ${BRAND.glow}`
    }
  }, "AE"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 12,
      color: BRAND.grey,
      letterSpacing: '0.15em'
    }
  }, "@ALLEN.ENRIQUEZ"));
}
function Hook() {
  const {
    time
  } = useTimeline();
  // Show the "5 minutes" countdown ticker as persistent overlay
  const remaining = Math.max(0, DURATION - time);
  const totalFake = 5 * 60;
  const displayed = Math.floor(totalFake - time / DURATION * (60 + 30));
  const m = Math.floor(displayed / 60);
  const s = displayed % 60;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 28,
      left: 48,
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      zIndex: 100
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 12,
      height: 12,
      borderRadius: '50%',
      background: BRAND.orange,
      boxShadow: `0 0 14px ${BRAND.orange}`,
      animation: 'aeblink 1s steps(2) infinite'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: MONO,
      fontSize: 16,
      fontWeight: 500,
      color: BRAND.offwhite,
      letterSpacing: '0.12em'
    }
  }, "UNDER 5 MIN \xB7 ", String(m), ":", String(s).padStart(2, '0')));
}
function App() {
  return /*#__PURE__*/React.createElement(Stage, {
    width: 1080,
    height: 1920,
    duration: DURATION,
    background: BRAND.bg,
    persistKey: "ae-reel"
  }, /*#__PURE__*/React.createElement(BackgroundGrid, null), /*#__PURE__*/React.createElement(ProgressBar, null), /*#__PURE__*/React.createElement(Sprite, {
    start: 0,
    end: 3
  }, /*#__PURE__*/React.createElement(Step1_OpenSent, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 3,
    end: 9
  }, /*#__PURE__*/React.createElement(Step2_CopyEmails, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 9,
    end: 14
  }, /*#__PURE__*/React.createElement(Step3_Paste, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 14,
    end: 27
  }, /*#__PURE__*/React.createElement(Step4_Prompt, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 27,
    end: 32
  }, /*#__PURE__*/React.createElement(Step5_SaveProject, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 32,
    end: 36.5
  }, /*#__PURE__*/React.createElement(Step6_PasteInstructions, null)), /*#__PURE__*/React.createElement(Sprite, {
    start: 36.5,
    end: 42
  }, /*#__PURE__*/React.createElement(FinaleEmail, null)), TWEAKS.showTransitions && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(Sprite, {
    start: 2.7,
    end: 3.5
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "02",
    title: "Copy your 10 emails."
  })), /*#__PURE__*/React.createElement(Sprite, {
    start: 8.7,
    end: 9.5
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "03",
    title: "Paste them into AI."
  })), /*#__PURE__*/React.createElement(Sprite, {
    start: 13.7,
    end: 14.5
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "04",
    title: "Write this prompt."
  })), /*#__PURE__*/React.createElement(Sprite, {
    start: 26.7,
    end: 27.5
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "05",
    title: "Save as a project."
  })), /*#__PURE__*/React.createElement(Sprite, {
    start: 31.7,
    end: 32.5
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "06",
    title: "Paste the instructions."
  })), /*#__PURE__*/React.createElement(Sprite, {
    start: 36.2,
    end: 37.0
  }, /*#__PURE__*/React.createElement(StepTransition, {
    step: "\u2713",
    title: "Every email sounds like you."
  }))), /*#__PURE__*/React.createElement(Watermark, null), /*#__PURE__*/React.createElement(Hook, null));
}
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(/*#__PURE__*/React.createElement(App, null));

// ── Tweaks wiring ────────────────────────────────────────────────────────
window.addEventListener('message', e => {
  const data = e.data || {};
  if (data.type === '__activate_edit_mode') {
    showTweakPanel();
  } else if (data.type === '__deactivate_edit_mode') {
    hideTweakPanel();
  }
});
window.parent.postMessage({
  type: '__edit_mode_available'
}, '*');
function showTweakPanel() {
  if (document.getElementById('ae-tweaks')) return;
  const panel = document.createElement('div');
  panel.id = 'ae-tweaks';
  panel.style.cssText = `
    position: fixed; bottom: 80px; right: 20px; z-index: 99999;
    background: rgba(10,22,40,0.96); border: 1px solid rgba(78,179,242,0.35);
    border-radius: 12px; padding: 16px; width: 260px;
    box-shadow: 0 0 40px rgba(78,179,242,0.3);
    font-family: 'Roboto Mono', monospace; color: #E8EEF5;
    backdrop-filter: blur(10px);
  `;
  panel.innerHTML = `
    <div style="font-size:11px; letter-spacing:0.2em; color:#4EB3F2; margin-bottom:14px; font-weight:500;">TWEAKS</div>
    <label style="display:block; margin-bottom:12px; font-size:12px;">
      <span style="display:block; margin-bottom:6px; color:#98A2B3;">Accent color</span>
      <input type="color" id="tw-accent" value="${TWEAKS.accent}" style="width:100%; height:32px; border:none; background:none; cursor:pointer;"/>
    </label>
    <label style="display:flex; align-items:center; gap:8px; margin-bottom:10px; font-size:12px; cursor:pointer;">
      <input type="checkbox" id="tw-transitions" ${TWEAKS.showTransitions ? 'checked' : ''}/>
      <span>Step transitions</span>
    </label>
    <label style="display:flex; align-items:center; gap:8px; font-size:12px; cursor:pointer;">
      <input type="checkbox" id="tw-progress" ${TWEAKS.showProgressBar ? 'checked' : ''}/>
      <span>Progress bar</span>
    </label>
  `;
  document.body.appendChild(panel);
  document.getElementById('tw-accent').addEventListener('input', e => {
    TWEAKS.accent = e.target.value;
    BRAND.accent = e.target.value;
    window.parent.postMessage({
      type: '__edit_mode_set_keys',
      edits: {
        accent: e.target.value
      }
    }, '*');
    // Force rerender
    root.render(/*#__PURE__*/React.createElement(App, null));
  });
  document.getElementById('tw-transitions').addEventListener('change', e => {
    TWEAKS.showTransitions = e.target.checked;
    window.parent.postMessage({
      type: '__edit_mode_set_keys',
      edits: {
        showTransitions: e.target.checked
      }
    }, '*');
    root.render(/*#__PURE__*/React.createElement(App, null));
  });
  document.getElementById('tw-progress').addEventListener('change', e => {
    TWEAKS.showProgressBar = e.target.checked;
    window.parent.postMessage({
      type: '__edit_mode_set_keys',
      edits: {
        showProgressBar: e.target.checked
      }
    }, '*');
    root.render(/*#__PURE__*/React.createElement(App, null));
  });
}
function hideTweakPanel() {
  const p = document.getElementById('ae-tweaks');
  if (p) p.remove();
}