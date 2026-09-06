const form = document.querySelector("#shorten-form");
const urlInput = document.querySelector("#target-url");
const submitButton = document.querySelector("#submit-button");
const formMessage = document.querySelector("#form-message");
const result = document.querySelector("#result");
const shortUrl = document.querySelector("#short-url");
const copyButton = document.querySelector("#copy-button");
const openButton = document.querySelector("#open-button");
const journeyToggles = document.querySelectorAll(".journey-toggle");
const apiBaseUrl = document
  .querySelector('meta[name="linkmint-api-base"]')
  .content.replace(/\/$/, "");

/** Toggle the form controls while a shortening request is active. */
function setSubmitting(isSubmitting) {
  submitButton.disabled = isSubmitting;
  urlInput.disabled = isSubmitting;
  submitButton.querySelector(".button-label").textContent = isSubmitting
    ? "Creating…"
    : "Shorten link";
}

/** Present a successful shortened link and its actions. */
function showResult(value) {
  shortUrl.textContent = value;
  shortUrl.href = value;
  openButton.href = value;
  result.hidden = false;
  formMessage.textContent = "";
  result.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/** Convert FastAPI validation details into a useful short message. */
function getErrorMessage(payload) {
  if (Array.isArray(payload?.detail) && payload.detail[0]?.msg) {
    return payload.detail[0].msg.replace(/^Value error, /, "");
  }
  return typeof payload?.detail === "string"
    ? payload.detail
    : "We could not shorten that URL. Please try again.";
}

/** Ask the API to persist a destination and return its new short link. */
async function createShortLink(targetUrl) {
  const response = await fetch(`${apiBaseUrl}/links`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_url: targetUrl }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(getErrorMessage(payload));
  }
  return payload;
}

/** Submit a URL to the same-origin FastAPI backend. */
async function handleSubmit(event) {
  event.preventDefault();
  result.hidden = true;
  formMessage.textContent = "";

  if (!urlInput.checkValidity()) {
    formMessage.textContent = "Enter a complete URL beginning with http:// or https://.";
    urlInput.focus();
    return;
  }

  setSubmitting(true);
  try {
    const payload = await createShortLink(urlInput.value.trim());
    showResult(payload.short_url);
  } catch (error) {
    formMessage.textContent = error.message || "The service is unavailable right now.";
  } finally {
    setSubmitting(false);
  }
}

/** Expose the visible shorten action to browsers that support WebMCP. */
function registerShortenTool() {
  const context = document.modelContext;
  if (!context?.registerTool) {
    return;
  }

  const lifecycle = new AbortController();
  void Promise.resolve(
    context.registerTool(
      {
        name: "create_short_link",
        title: "Create short link",
        description: "Create and display a LinkMint short URL for an HTTP or HTTPS destination.",
        inputSchema: {
          type: "object",
          properties: {
            targetUrl: {
              type: "string",
              format: "uri",
              description: "The complete HTTP or HTTPS destination URL.",
            },
          },
          required: ["targetUrl"],
          additionalProperties: false,
        },
        annotations: { readOnlyHint: false, untrustedContentHint: true },
        async execute(input) {
          const parsedUrl = new URL(input.targetUrl);
          if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
            throw new Error("targetUrl must begin with http:// or https://");
          }
          urlInput.value = parsedUrl.href;
          const payload = await createShortLink(parsedUrl.href);
          showResult(payload.short_url);
          return {
            shortCode: payload.short_code,
            shortUrl: payload.short_url,
          };
        },
      },
      { signal: lifecycle.signal },
    ),
  ).catch(() => {
    // The visible form remains available when browser tool registration fails.
  });
}

/** Copy the generated short link and briefly confirm success. */
async function copyGeneratedLink() {
  try {
    await navigator.clipboard.writeText(shortUrl.href);
    copyButton.textContent = "Copied!";
    window.setTimeout(() => {
      copyButton.textContent = "Copy";
    }, 1800);
  } catch {
    formMessage.textContent = "Copy failed. Select the link and copy it manually.";
  }
}

/** Expand one API journey at a time while keeping the controls accessible. */
function toggleJourney(selectedToggle) {
  const selectedPanel = document.querySelector(
    `#${selectedToggle.dataset.journeyTarget}`,
  );
  const shouldOpen = selectedToggle.getAttribute("aria-expanded") !== "true";

  journeyToggles.forEach((toggle) => {
    const panel = document.querySelector(`#${toggle.dataset.journeyTarget}`);
    toggle.setAttribute("aria-expanded", "false");
    panel.hidden = true;
  });

  if (shouldOpen) {
    selectedToggle.setAttribute("aria-expanded", "true");
    selectedPanel.hidden = false;
  }
}

form.addEventListener("submit", handleSubmit);
copyButton.addEventListener("click", copyGeneratedLink);
journeyToggles.forEach((toggle) => {
  toggle.addEventListener("click", () => toggleJourney(toggle));
});
registerShortenTool();
