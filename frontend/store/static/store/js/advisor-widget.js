(function (global) {
  function formatTime(date) {
    return date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  }

  function createWidgetMarkup(options) {
    const chips = (options.suggestionChips || [])
      .map(function (chip) {
        return '<button type="button" class="advisor-chip-btn" data-chip="' + chip.replace(/"/g, "&quot;") + '">' + chip + "</button>";
      })
      .join("");

    return (
      '<button type="button" class="advisor-chat-toggle">AI Advisor Chat</button>' +
      '<div class="advisor-chat-panel hidden">' +
      '  <div class="advisor-chat-head">' +
      '    <div class="advisor-chat-head-main">' +
      '      <p class="advisor-chat-title">Tro ly mua sam AI</p>' +
      '      <p class="advisor-chat-subtitle">Hoi nhanh de nhan tu van dung nhu cau</p>' +
      "    </div>" +
      '    <button type="button" class="advisor-chat-expand" aria-pressed="false">Toan man hinh</button>' +
      "  </div>" +
      '  <div class="advisor-chat-status" data-mode="ready">Trang thai: san sang</div>' +
      (chips ? '<div class="advisor-chat-chips">' + chips + "</div>" : "") +
      '<div class="advisor-chat-messages"></div>' +
      '  <form class="advisor-chat-form">' +
      '    <input name="message" type="text" placeholder="Hoi cach chon laptop, dien thoai, quan ao..." />' +
      '    <button type="submit">Gui</button>' +
      "  </form>" +
      "</div>"
    );
  }

  function saveHistory(storageKey, messages) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(messages.slice(-10)));
    } catch (error) {
      // Ignore storage errors.
    }
  }

  function loadHistory(storageKey) {
    try {
      var raw = localStorage.getItem(storageKey);
      if (!raw) {
        return [];
      }
      var parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function initAdvisorWidget(options) {
    options = options || {};
    var mount = document.querySelector(options.mountSelector || "body");
    if (!mount) {
      return;
    }

    var widget = document.createElement("div");
    widget.className = "advisor-chat-widget";
    widget.innerHTML = createWidgetMarkup(options);
    mount.appendChild(widget);

    var toggle = widget.querySelector(".advisor-chat-toggle");
    var panel = widget.querySelector(".advisor-chat-panel");
    var statusLine = widget.querySelector(".advisor-chat-status");
    var messages = widget.querySelector(".advisor-chat-messages");
    var form = widget.querySelector(".advisor-chat-form");
    var expandBtn = widget.querySelector(".advisor-chat-expand");
    var chipsWrap = widget.querySelector(".advisor-chat-chips");
    var storageKey = options.storageKey || "advisor-chat-history-home";

    var opened = false;
    var isFullscreen = false;
    var history = loadHistory(storageKey);

    function scrollToBottom() {
      messages.scrollTop = messages.scrollHeight;
    }

    function setStatus(text, mode) {
      if (!statusLine) {
        return;
      }
      statusLine.textContent = "Trang thai: " + text;
      statusLine.dataset.mode = mode || "ready";
    }

    function formatPrice(value) {
      var amount = Number(value || 0);
      if (!Number.isFinite(amount) || amount <= 0) {
        return "Lien he";
      }
      return amount.toLocaleString("vi-VN") + "đ";
    }

    function behaviorLabel(label) {
      var mapping = {
        impulse_buyer: "mua nhanh",
        researcher: "nghien cuu ky",
        loyal_customer: "khach quay lai",
        price_sensitive: "nhay gia",
        window_shopper: "tham khao",
        uncertain: "chua ro",
      };
      return mapping[label] || (label || "chua ro");
    }

    function appendMessage(role, text, timestampText) {
      var line = document.createElement("div");
      line.className = "advisor-chat-line " + role;

      var avatar = document.createElement("span");
      avatar.className = "advisor-chat-avatar";
      avatar.textContent = role === "user" ? "YOU" : "AI";

      var wrap = document.createElement("div");
      wrap.className = "advisor-chat-bubble-wrap";

      var bubble = document.createElement("div");
      bubble.className = "advisor-chat-bubble";
      bubble.textContent = text;

      var time = document.createElement("span");
      time.className = "advisor-chat-time";
      time.textContent = timestampText || formatTime(new Date());

      wrap.appendChild(bubble);
      wrap.appendChild(time);
      line.appendChild(avatar);
      line.appendChild(wrap);
      messages.appendChild(line);
      scrollToBottom();

      history.push({ role: role, text: text, timestamp: time.textContent });
      saveHistory(storageKey, history);

      return line;
    }

    function appendSourceLine(sourceAttribution) {
      if (!sourceAttribution || !sourceAttribution.text) {
        return;
      }
      var sourceLine = document.createElement("div");
      sourceLine.className = "advisor-chat-source-line";
      sourceLine.textContent = "Source: " + sourceAttribution.text;
      messages.appendChild(sourceLine);
      scrollToBottom();
    }

    function appendInsightCard(summary) {
      var profile = summary && summary.behavior_profile;
      if (!profile || !profile.label) {
        return;
      }

      var card = document.createElement("div");
      card.className = "advisor-chat-insight";

      var title = document.createElement("strong");
      title.className = "advisor-chat-insight-title";
      title.textContent = "AI dang toi uu theo hanh vi cua ban";

      var body = document.createElement("p");
      body.className = "advisor-chat-insight-text";
      body.textContent =
        "Ho so hien tai: " +
        behaviorLabel(profile.label) +
        " • do tin cay " +
        Math.round(Number(profile.confidence || 0) * 100) +
        "%";

      var meta = document.createElement("div");
      meta.className = "advisor-chat-insight-meta";
      meta.textContent =
        "Model: " +
        String(profile.selected_model || profile.mode || "mlp").toUpperCase() +
        (profile.selected_model_score ? " • F1 " + profile.selected_model_score : "");

      card.appendChild(title);
      card.appendChild(body);
      card.appendChild(meta);
      messages.appendChild(card);
      scrollToBottom();
    }

    function appendRecommendationCards(items) {
      if (!Array.isArray(items) || !items.length) {
        return;
      }

      var wrap = document.createElement("div");
      wrap.className = "advisor-chat-recommendations";

      var title = document.createElement("strong");
      title.className = "advisor-chat-recommendations-title";
      title.textContent = "Goi y nhanh cho ban";
      wrap.appendChild(title);

      items.slice(0, 3).forEach(function (item) {
        var link = document.createElement("a");
        link.className = "advisor-recommendation-card";
        link.href = "/products/" + (item.product_type || "computer") + "/" + item.id;

        var name = document.createElement("span");
        name.className = "advisor-recommendation-name";
        name.textContent = item.name || "San pham";

        var meta = document.createElement("span");
        meta.className = "advisor-recommendation-meta";
        meta.textContent =
          String(item.product_type || "").toUpperCase() +
          " • " +
          formatPrice(item.price);

        var reason = document.createElement("span");
        reason.className = "advisor-recommendation-reason";
        reason.textContent = item.reason || "Phu hop voi nhu cau dang hoi";

        link.appendChild(name);
        link.appendChild(meta);
        link.appendChild(reason);
        wrap.appendChild(link);
      });

      messages.appendChild(wrap);
      scrollToBottom();
    }

    function showTypingIndicator() {
      var line = document.createElement("div");
      line.className = "advisor-chat-line bot typing";

      var avatar = document.createElement("span");
      avatar.className = "advisor-chat-avatar";
      avatar.textContent = "AI";

      var wrap = document.createElement("div");
      wrap.className = "advisor-chat-bubble-wrap";

      var bubble = document.createElement("div");
      bubble.className = "advisor-chat-bubble";
      bubble.textContent = "Dang soan";

      var dots = document.createElement("span");
      dots.className = "advisor-typing-dots";
      dots.innerHTML = "<span></span><span></span><span></span>";
      bubble.appendChild(dots);

      var time = document.createElement("span");
      time.className = "advisor-chat-time";
      time.textContent = formatTime(new Date());

      wrap.appendChild(bubble);
      wrap.appendChild(time);
      line.appendChild(avatar);
      line.appendChild(wrap);
      messages.appendChild(line);
      scrollToBottom();
      return line;
    }

    function setFullscreen(nextState) {
      isFullscreen = nextState;
      widget.classList.toggle("is-fullscreen", isFullscreen);
      expandBtn.setAttribute("aria-pressed", isFullscreen ? "true" : "false");
      expandBtn.textContent = isFullscreen ? "Thu nho" : "Toan man hinh";
      if (isFullscreen) {
        panel.classList.remove("hidden");
      }
      scrollToBottom();
    }

    history.forEach(function (item) {
      appendMessage(item.role, item.text, item.timestamp);
    });

    if (!history.length) {
      appendMessage("bot", "Xin chao! Ban can tu van nhanh ve laptop, dien thoai hay phu kien nao?");
    }

    expandBtn.addEventListener("click", function () {
      setFullscreen(!isFullscreen);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && isFullscreen) {
        setFullscreen(false);
      }
    });

    toggle.addEventListener("click", async function () {
      panel.classList.toggle("hidden");
      if (!opened) {
        opened = true;
        try {
          await fetch(options.eventUrl || "/advisor/event", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ event_type: "chat_open", metadata: { page: options.pageName || "home" } }),
          });
        } catch (error) {
          // Ignore event tracking failures.
        }
      }
    });

    if (chipsWrap) {
      chipsWrap.addEventListener("click", function (event) {
        var target = event.target;
        if (!target || !target.dataset || !target.dataset.chip) {
          return;
        }
        var input = form.querySelector("input[name='message']");
        input.value = target.dataset.chip;
        input.focus();
      });
    }

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      var input = form.querySelector("input[name='message']");
      var message = (input.value || "").trim();
      if (!message) {
        return;
      }

      appendMessage("user", message);
      input.value = "";
      setStatus("dang tao cau tra loi...", "generating");
      var typingLine = showTypingIndicator();

      try {
        var response = await fetch(options.chatUrl || "/advisor/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: message, language: "vi" }),
        });
        var payload = await response.json();
        typingLine.remove();

        var answer = payload.answer || payload.error || "Khong co phan hoi tu AI advisor.";
        appendMessage("bot", answer);
        appendInsightCard(payload.summary || {});
        appendRecommendationCards(payload.recommendations || []);
        appendSourceLine(payload.source_attribution);

        var stateMap = {
          generated: "cloud model",
          fallback: "fallback noi bo",
          no_evidence: "thieu bang chung",
          blocked: "bi chan boi guardrails",
          grounding_failed: "can xac minh them",
        };
        setStatus(stateMap[payload.ai_status] || "san sang", payload.ai_status || "ready");
      } catch (error) {
        typingLine.remove();
        appendMessage("bot", "He thong tam gap qua tai, vui long thu lai.");
        setStatus("loi ket noi", "error");
      }
    });
  }

  global.initAdvisorWidget = initAdvisorWidget;
})(window);
