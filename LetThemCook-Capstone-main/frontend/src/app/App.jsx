// =============================================================================
// App.jsx — Main React Component (UI Shell Only)
import { useState, useRef, useEffect } from "react";
import {
  X,
  Send,
  Search,
  Plus,
  ChefHat,
  Leaf,
  Clock,
  UtensilsCrossed,
  MessageSquare,
  BookOpen,
  CheckCircle2,
  PlusCircle,
  ChevronDown,
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

// ── Recipe data & search service ──────────────────────────────────────────────
import { searchRecipes, chatWithChef, getSystemHealth } from "./services/recipeService.js";

// ── Text / label config (edit these files, not this one) ─────────────────────
import {
  WELCOME_MESSAGE,
  QUICK_PROMPTS,
  CHAT_HEADER,
  CHAT_INPUT_HINT,
  CHAT_INPUT_PLACEHOLDER,
} from "./config/chat.config.js";

import {
  APP_IDENTITY,
  MEAL_FILTERS,
  INGREDIENT_INPUT,
  SEARCH_BAR,
  STATUS_BAR,
  HOW_IT_WORKS,
  RECIPE_CARD_LABELS,
  RECIPE_MODAL,
  EMPTY_STATE,
  MOBILE_TABS,
} from "./config/ui.config.js";

// ── Local types and initial data ───────────────────────────────────────────────
const WELCOME = { id: "0", role: "assistant", content: WELCOME_MESSAGE };

// ─── Components (defined OUTSIDE App to avoid re-mount on every render) ───────
function formatTotalTime(minutes) {
  if (!minutes && minutes !== 0) return "—";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h} hr`;
  return `${h} hr ${m} min`;
}

function sanitizeIngredientInput(value) {
  return value.replace(/[^a-zA-Z, -]/g, "");
}
/**
 * MealBadge - Shows the meal type (Breakfast, Lunch, Dinner)
 */
function MealBadge({ type }) {
  const styles = {
    Breakfast: "bg-amber-50 text-amber-700 border-amber-200",
    Lunch: "bg-sky-50 text-sky-700 border-sky-200",
    Dinner: "bg-violet-50 text-violet-700 border-violet-200",
  };
  return (
    <span
      className={`inline-flex items-center text-[10px] font-semibold uppercase tracking-wide px-2.5 py-0.5 rounded-full border ${styles[type]}`}
      style={{ fontFamily: "'DM Mono', monospace" }}
    >
      {type}
    </span>
  );
}

/**
 * AvailableLabel - Green badge shown when all core ingredients are available
 */
function AvailableLabel() {
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full"
      style={{ fontFamily: "'DM Mono', monospace" }}
    >
      <CheckCircle2 size={10} />
      {RECIPE_CARD_LABELS.availableOnly}
    </span>
  );
}

/**
 * AdditionalLabel - Orange badge shown when some additional ingredients are needed
 */
function AdditionalLabel() {
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-semibold text-orange-700 bg-orange-50 border border-orange-200 px-2.5 py-0.5 rounded-full"
      style={{ fontFamily: "'DM Mono', monospace" }}
    >
      <PlusCircle size={10} />
      {RECIPE_CARD_LABELS.withAdditional}
    </span>
  );
}

/**
 * TypingDots - Animated dots shown while AI is thinking
 */
function TypingDots() {
  return (
    <div className="flex gap-1 px-4 py-3 items-center">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full bg-primary/40"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.18 }}
        />
      ))}
    </div>
  );
}

/**
 * RecipeModal - Detailed recipe popup shown when user clicks a recipe card
 */
function RecipeModal({ r, onClose, hasPantry }) {
  const isAvailableOnly = hasPantry && r.tier === 1;
  const hasAdditional = hasPantry && r.missingLines.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.93, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0, y: 8 }}
        transition={{ type: "spring", stiffness: 340, damping: 28 }}
        className="w-full max-w-lg max-h-[92vh] bg-white rounded-3xl shadow-2xl border border-stone-100 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal top header */}
        <div className="flex-shrink-0 relative text-center px-10 pt-7 pb-5 bg-gradient-to-b from-stone-50 to-white border-b border-stone-100">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-9 h-9 rounded-full bg-stone-100 hover:bg-stone-200 flex items-center justify-center transition-colors group"
          >
            <X
              size={15}
              className="text-stone-400 group-hover:text-stone-600 transition-colors"
            />
          </button>

          <h2
            className="text-2xl font-bold text-stone-800 pr-4"
            style={{ fontFamily: "'Lora', serif" }}
          >
            {r.name}
          </h2>

          {/* Availability label */}
          {hasPantry && (
            <div className="flex justify-center mt-2.5">
              {isAvailableOnly ? <AvailableLabel /> : <AdditionalLabel />}
            </div>
          )}

          <div className="flex justify-center mt-1.5">
            <MealBadge type={r.mealType} />
          </div>

       {/* Total time */}
<div
  className="flex justify-center mt-5 text-sm"
  style={{ fontFamily: "'DM Sans', sans-serif" }}
>
  <div className="px-5 text-center">
    <p
      className="text-[9px] uppercase tracking-[0.15em] text-stone-400 font-semibold"
      style={{ fontFamily: "'DM Mono', monospace" }}
    >
      {RECIPE_MODAL.totalTimeLabel}
    </p>
    <p className="font-semibold text-stone-700 mt-0.5">
      {formatTotalTime(r.timeMinutes)}
    </p>
  </div>
</div>

          {/* Cooking method */}
          <div className="mt-4 inline-flex items-center gap-1.5 bg-stone-100 rounded-full px-4 py-1.5">
            <UtensilsCrossed size={11} className="text-stone-400" />
            <span
              className="text-xs text-stone-500 font-medium"
              style={{ fontFamily: "'DM Mono', monospace" }}
            >
              {r.cookingMethod}
            </span>
          </div>
        </div>

        {/* Scrollable body */}
        <div
          className="flex-1 overflow-y-auto px-7 py-6 space-y-7"
          style={{ scrollbarWidth: "thin", scrollbarColor: "#d6d3d1 transparent" }}
        >
          {/* ── INGREDIENTS ── */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="flex-1 h-px bg-stone-100" />
              <h3
                className="text-xs font-bold uppercase tracking-[0.22em] text-stone-500 flex items-center gap-1.5"
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                <Leaf size={11} /> {RECIPE_MODAL.ingredientsHeading}
              </h3>
              <div className="flex-1 h-px bg-stone-100" />
            </div>

            {/* No pantry: show all ingredients normally */}
            {!hasPantry && (
              <ul className="space-y-2 text-center">
                {r.allIngredients.map((ing, i) => (
                  <li
                    key={i}
                    className="text-sm text-stone-600"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    {ing}
                  </li>
                ))}
              </ul>
            )}

            {/* Available only: show with green dots */}
            {hasPantry && isAvailableOnly && (
              <ul className="space-y-2.5">
                {r.availLines.map((ing, i) => (
                  <li
                    key={i}
                    className="flex items-center gap-3 text-sm text-stone-700"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                    {ing}
                  </li>
                ))}
                {r.missingLines.map((ing, i) => (
                  <li
                    key={`m-${i}`}
                    className="flex items-center gap-3 text-sm text-stone-500"
                    style={{ fontFamily: "'DM Sans', sans-serif" }}
                  >
                    <span className="w-2 h-2 rounded-full bg-stone-200 flex-shrink-0" />
                    {ing}
                  </li>
                ))}
              </ul>
            )}

            {/* Additional ingredients needed */}
            {hasPantry && !isAvailableOnly && (
              <>
                {/* Available ingredients section */}
                {r.availLines.length > 0 && (
                  <div className="mb-4">
                    <div className="inline-flex items-center gap-1.5 mb-3">
                      <CheckCircle2 size={12} className="text-emerald-500" />
                      <span
                        className="text-[10px] font-bold uppercase tracking-wide text-emerald-600"
                        style={{ fontFamily: "'DM Mono', monospace" }}
                      >
                        {RECIPE_MODAL.availableSubLabel}
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {r.availLines.map((ing, i) => (
                        <li
                          key={i}
                          className="flex items-center gap-3 text-sm text-stone-700"
                          style={{ fontFamily: "'DM Sans', sans-serif" }}
                        >
                          <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                          {ing}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Divider */}
                {r.availLines.length > 0 && r.missingLines.length > 0 && (
                  <div className="flex items-center gap-3 my-4">
                    <div className="flex-1 h-px bg-orange-100" />
                    <div className="flex items-center gap-1.5">
                      <PlusCircle size={10} className="text-orange-400" />
                      <span
                        className="text-[10px] font-bold uppercase tracking-wide text-orange-500"
                        style={{ fontFamily: "'DM Mono', monospace" }}
                      >
                        {RECIPE_MODAL.additionalDivider}
                      </span>
                    </div>
                    <div className="flex-1 h-px bg-orange-100" />
                  </div>
                )}

                {/* Missing ingredients section */}
                {r.missingLines.length > 0 && (
                  <ul className="space-y-2">
                    {r.missingLines.map((ing, i) => (
                      <li
                        key={i}
                        className="flex items-center gap-3 text-sm text-stone-500"
                        style={{ fontFamily: "'DM Sans', sans-serif" }}
                      >
                        <span className="w-2 h-2 rounded-full bg-orange-300 flex-shrink-0" />
                        {ing}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>

          {/* Show pantry items that are not used by this selected recipe. */}
          {hasPantry && (r.unusedPantry || []).length > 0 && (
            <section className="rounded-2xl border border-amber-100 bg-amber-50/60 px-4 py-4">
              <h3
                className="text-[10px] font-bold uppercase tracking-[0.18em] text-amber-700 mb-2"
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                Unused pantry ingredients
              </h3>
              <p
                className="text-xs text-stone-500 mb-2"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                These items are in your pantry but are not needed for this recipe.
              </p>
              <div className="flex flex-wrap gap-2">
                {r.unusedPantry.map((ingredient) => (
                  <span
                    key={ingredient}
                    className="text-xs rounded-full border border-amber-200 bg-white px-2.5 py-1 text-amber-700"
                    style={{ fontFamily: "'DM Mono', monospace" }}
                  >
                    {ingredient}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* ── INSTRUCTIONS ── */}
          <section>
            <div className="flex items-center gap-3 mb-5">
              <div className="flex-1 h-px bg-stone-100" />
              <h3
                className="text-xs font-bold uppercase tracking-[0.22em] text-stone-500 flex items-center gap-1.5"
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                <Clock size={11} /> {RECIPE_MODAL.instructionsHeading}
              </h3>
              <div className="flex-1 h-px bg-stone-100" />
            </div>
            <ol className="space-y-4">
              {r.instructions.map((step, i) => (
                <li
                  key={i}
                  className="flex gap-3.5 text-sm text-stone-600 leading-relaxed"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                >
                  <span
                    className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold flex items-center justify-center mt-0.5"
                    style={{ fontFamily: "'DM Mono', monospace" }}
                  >
                    {i + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </section>
        </div>
      </motion.div>
    </motion.div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────

/**
 * App - Main application component
 * Renders the recipe browser and AI chat interface
 */
export default function App() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [pantry, setPantry] = useState([]);
  const [inputVal, setInputVal] = useState("");
  const [activeFilter, setActiveFilter] = useState("All");
  const [nameSearch, setNameSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [messages, setMessages] = useState([WELCOME]);
  const [chatInput, setChatInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [mobileTab, setMobileTab] = useState("recipes");
  const [ranked, setRanked] = useState([]);
  const [showQuickPrompts, setShowQuickPrompts] = useState(true);
  const [recipeSource, setRecipeSource] = useState("checking");
  const [systemHealth, setSystemHealth] = useState(null);

  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  // ── Effects ────────────────────────────────────────────────────────────────

  // Auto-scroll chat to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Auto-expand textarea as user types
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [chatInput]);

  // Check the real backend, Ollama, model, and ChromaDB status.
  // The first check runs when the page opens, then repeats every 60 seconds.
  useEffect(() => {
    let active = true;

    const checkHealth = async () => {
      try {
        const health = await getSystemHealth();
        if (active) setSystemHealth(health);
      } catch (error) {
        console.warn("Local backend health check failed:", error);
        if (active) {
          setSystemHealth({
            backend_ready: false,
            status: "offline",
          });
        }
      }
    };

    checkHealth();
    const timer = window.setInterval(checkHealth, 60000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  // Ask the backend to rank recipes whenever pantry/filter/search changes.
  // A 300 ms debounce stops one API request from being sent for every key press.
  useEffect(() => {
    let active = true;

    const timer = window.setTimeout(() => {
      searchRecipes(pantry, activeFilter, nameSearch)
        .then(({ results, source }) => {
          if (active) {
            setRanked(results);
            setRecipeSource(source);
          }
        })
        .catch((error) => {
          console.error("Recipe search failed:", error);
          if (active) {
            setRanked([]);
            setRecipeSource("error");
          }
        });
    }, 300);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [pantry, activeFilter, nameSearch]);

  // ── Handlers ───────────────────────────────────────────────────────────────

  /**
   * Add ingredient(s) to the pantry
   * Supports comma-separated input
   */
  const addIngredient = () => {
    const parts = inputVal
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (parts.length === 0) return;

    const lower = pantry.map((p) => p.toLowerCase());
    const newOnes = parts.filter((p) => !lower.includes(p.toLowerCase()));

    if (newOnes.length === 0) {
      setInputVal("");
      return;
    }

    setPantry((prev) => [...prev, ...newOnes]);
    setInputVal("");
  };

  /**
   * Remove ingredient from pantry by index
   */
  const removeIngredient = (i) =>
    setPantry((prev) => prev.filter((_, idx) => idx !== i));

  /**
   * Handle Enter key in ingredient input
   */
  const handleIngKey = (e) => {
    if (e.key === "Enter") addIngredient();
  };

  const hasPantry = pantry.length > 0;

  /**
   * Send message to the FastAPI backend and render Chef Llama's reply.
   */
  const sendMsg = async (text) => {
    const content = (text ?? chatInput).trim();
    if (!content || isTyping) return;

    // Send only real conversation messages. The welcome message is UI text and
    // does not need to be repeated to Llama. Limit history to keep prompts small.
    const history = messages
      .filter((message) => message.id !== "0")
      .slice(-12)
      .map(({ role, content: messageContent }) => ({
        role,
        content: messageContent,
      }));

    setMessages((previous) => [
      ...previous,
      { id: Date.now().toString(), role: "user", content },
    ]);
    setChatInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    setIsTyping(true);

    try {
      const reply = await chatWithChef(content, history);
      setMessages((previous) => [
        ...previous,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: reply,
        },
      ]);
    } catch (error) {
      console.error("Backend chat failed:", error);
      setMessages((previous) => [
        ...previous,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content:
            "I cannot connect to the local backend. Please run the Python server and Ollama, then try again. 🍳",
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  /**
   * Handle Enter key in chat input
   * Sends message on Enter, allows Shift+Enter for new line
   */
  const handleChatKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMsg();
    }
  };

  // Build one truthful status object for both the recipe and chat headers.
  // This replaces the old hardcoded green "online" badge.
  const connectionStatus = (() => {
    if (!systemHealth) {
      return {
        label: "Checking local services…",
        container: "bg-stone-50 border-stone-200",
        dot: "bg-stone-400",
        text: "text-stone-500",
      };
    }

    if (!systemHealth.backend_ready || recipeSource === "frontend_fallback") {
      return {
        label: "Offline",
        container: "bg-amber-50 border-amber-200",
        dot: "bg-amber-400",
        text: "text-amber-700",
      };
    }

    if (!systemHealth.ollama_ready || !systemHealth.model_ready) {
      return {
        label: "Local catalog · AI offline",
        container: "bg-amber-50 border-amber-200",
        dot: "bg-amber-400",
        text: "text-amber-700",
      };
    }

    if (!systemHealth.chroma_query_ready) {
      return {
        label: "Local · Chroma unavailable",
        container: "bg-amber-50 border-amber-200",
        dot: "bg-amber-400",
        text: "text-amber-700",
      };
    }

    return {
      label: "Llama 3.2 3B · Local",
      container: "bg-emerald-50 border-emerald-200",
      dot: "bg-emerald-400",
      text: "text-emerald-600",
    };
  })();

  // ── Recipe Panel JSX ───────────────────────────────────────────────────────
  const recipePanel = (
    <div className="flex flex-col h-full min-h-0 bg-[#f9f6f1]">
      {/* Header */}
      <header className="flex-shrink-0 px-5 lg:px-7 pt-5 pb-4 bg-white border-b border-stone-100 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-primary flex items-center justify-center shadow-md shadow-primary/25">
            <ChefHat size={18} className="text-white" />
          </div>
          <div>
            <h1
              className="text-xl font-bold text-stone-800 leading-none"
              style={{ fontFamily: "'Lora', serif" }}
            >
              {APP_IDENTITY.name}
            </h1>
            <p
              className="text-[10px] text-stone-400 tracking-[0.18em] uppercase mt-0.5"
              style={{ fontFamily: "'DM Mono', monospace" }}
            >
              {APP_IDENTITY.tagline}
            </p>
          </div>
          <div
            className={`ml-auto hidden sm:flex items-center gap-1.5 border rounded-full px-3 py-1.5 ${connectionStatus.container}`}
            title="Live status from the FastAPI /health endpoint"
          >
            <div className={`w-1.5 h-1.5 rounded-full ${connectionStatus.dot} animate-pulse`} />
            <span
              className={`text-[10px] font-medium ${connectionStatus.text}`}
              style={{ fontFamily: "'DM Mono', monospace" }}
            >
              {connectionStatus.label}
            </span>
          </div>
        </div>
      </header>

      {/* Ingredient input */}
      <div className="flex-shrink-0 px-5 lg:px-7 pt-5 pb-4 bg-white border-b border-stone-100">
        <label
          className="block text-[11px] font-bold uppercase tracking-[0.18em] text-stone-400 mb-1"
          style={{ fontFamily: "'DM Mono', monospace" }}
        >
          {INGREDIENT_INPUT.label}
        </label>
        <p
          className="text-[11px] text-stone-400 mb-2.5"
          style={{ fontFamily: "'DM Sans', sans-serif" }}
        >
          {INGREDIENT_INPUT.hint}
        </p>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={inputVal}
            onChange={(e) => setInputVal(sanitizeIngredientInput(e.target.value))}  
              onKeyDown={handleIngKey}
              placeholder={INGREDIENT_INPUT.placeholder}
              className="w-full text-sm bg-stone-50 border border-stone-200 rounded-xl px-4 py-2.5 text-stone-800 placeholder:text-stone-300 outline-none focus:border-primary/60 focus:ring-2 focus:ring-primary/10 transition-all"
            />
          </div>
          <button
            onClick={addIngredient}
            className="flex-shrink-0 h-10 px-5 rounded-xl bg-primary text-white text-[11px] font-bold uppercase tracking-wider hover:bg-primary/90 active:scale-95 transition-all shadow-sm shadow-primary/25 flex items-center gap-1.5"
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            <Plus size={14} /> {INGREDIENT_INPUT.addButton}
          </button>
        </div>

        {pantry.length > 0 && (
          <div className="mt-3">
            <div
              className="flex flex-wrap gap-2 overflow-y-auto pr-1"
              style={{
                maxHeight: "96px",
                scrollbarWidth: "thin",
                scrollbarColor: "#a7f3d0 transparent",
              }}
            >
              {pantry.map((ing, i) => (
                <motion.span
                  key={ing}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold flex-shrink-0"
                  style={{ fontFamily: "'DM Mono', monospace" }}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  {ing}
                  <button
                    onClick={() => removeIngredient(i)}
                    className="hover:text-red-500 transition-colors ml-0.5 w-3.5 h-3.5 flex items-center justify-center"
                    title="Remove ingredient"
                  >
                    <X size={10} />
                  </button>
                </motion.span>
              ))}
            </div>
            {/* Show count + clear all */}
            <div className="flex items-center justify-between mt-1.5">
              <span
                className="text-[10px] text-stone-400"
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                {pantry.length}{" "}
                {pantry.length !== 1
                  ? INGREDIENT_INPUT.countSuffixPlural
                  : INGREDIENT_INPUT.countSuffix}{" "}
                added
                {pantry.length > 6
                  ? " · " + INGREDIENT_INPUT.scrollHint
                  : ""}
              </span>
              <button
                onClick={() => setPantry([])}
                className="text-[10px] text-red-400 hover:text-red-600 transition-colors font-medium"
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                {INGREDIENT_INPUT.clearAll}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Filters + Search bar */}
      <div className="flex-shrink-0 px-5 lg:px-7 py-3 bg-white border-b border-stone-100 flex flex-wrap items-center gap-2">
        <span
          className="text-[10px] text-stone-400 uppercase tracking-wider mr-1 hidden sm:block"
          style={{ fontFamily: "'DM Mono', monospace" }}
        >
          {SEARCH_BAR.mealLabel}
        </span>
        {MEAL_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            className={`h-8 px-3.5 rounded-full text-[11px] font-bold uppercase tracking-wider border transition-all ${
              activeFilter === f
                ? "bg-primary text-white border-primary shadow-sm"
                : "border-stone-200 text-stone-500 hover:border-primary/50 hover:text-primary bg-stone-50"
            }`}
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            {f}
          </button>
        ))}
        <div className="flex-1 min-w-[110px] relative">
  <Search
    size={13}
    className="absolute left-3 top-1/2 -translate-y-1/2 text-stone-400 pointer-events-none"
  />
  <input
    type="text"
    value={nameSearch}
    onChange={(e) => setNameSearch(e.target.value)}
    placeholder={SEARCH_BAR.placeholder}
    className="w-full text-xs bg-white border-2 border-stone-300 rounded-full pl-8 pr-3 h-8 text-stone-700 placeholder:text-stone-400 outline-none shadow-sm hover:border-stone-400 focus:border-primary focus:ring-2 focus:ring-primary/10 transition-all"
  />
</div>
      </div>

      {/* Stats + ranking legend */}
      {hasPantry && (
        <div className="flex-shrink-0 px-5 lg:px-7 py-2.5 bg-stone-50/80 border-b border-stone-100 flex flex-wrap items-center gap-3">
          <span
            className="text-[10px] text-stone-500"
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            {STATUS_BAR.rankedPrefix}
          </span>
          <span
            className="inline-flex items-center gap-1 text-[10px] text-emerald-600"
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            <CheckCircle2 size={10} /> {ranked.filter((r) => r.tier === 1).length}{" "}
            {STATUS_BAR.perfect}
          </span>
          <span
            className="inline-flex items-center gap-1 text-[10px] text-orange-500"
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            <PlusCircle size={10} />{" "}
            {ranked.filter((r) => r.tier !== 1).length}{" "}
            {STATUS_BAR.withAdditional}
          </span>
          <span
            className="ml-auto text-[10px] text-stone-400"
            style={{ fontFamily: "'DM Mono', monospace" }}
          >
            {ranked.length} {STATUS_BAR.recipesSuffix}
          </span>
        </div>
      )}

      {/* Recipe grid */}
      <div
        className="flex-1 overflow-y-auto px-5 lg:px-7 py-5 min-h-0"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "#e5e0d5 transparent",
        }}
      >
        {/* How-to hint when no pantry */}
        {!hasPantry && (
          <div className="mb-4 p-3.5 bg-primary/5 border border-primary/15 rounded-2xl flex items-start gap-3">
            <span className="text-2xl mt-0.5">💡</span>
            <div>
              <p
                className="text-sm font-semibold text-stone-700"
                style={{ fontFamily: "'Lora', serif" }}
              >
                {HOW_IT_WORKS.title}
              </p>
              <p
                className="text-xs text-stone-500 mt-0.5 leading-relaxed"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                {HOW_IT_WORKS.body}
              </p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {ranked.map((r, idx) => (
            <motion.button
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.03, duration: 0.22 }}
              onClick={() => setSelected(r)}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                hasPantry && r.tier === 1
                  ? "bg-white border-emerald-200 hover:border-emerald-400 hover:shadow-md hover:shadow-emerald-100"
                  : "bg-white border-stone-200 hover:border-stone-300 hover:shadow-md hover:shadow-stone-100"
              }`}
              style={{ boxShadow: "0 1px 3px rgba(0,0,0,0.05)" }}
            >
              <div className="flex items-start gap-3">
                {/* Rank number */}
                <span
                  className="text-3xl font-bold leading-none flex-shrink-0 w-12 text-right transition-colors text-stone-200 group-hover:text-primary/20"
                  style={{ fontFamily: "'Lora', serif" }}
                >
                  {idx + 1}
                </span>

                <div className="flex-1 min-w-0">
                  <p
                    className="font-semibold text-stone-800 group-hover:text-primary transition-colors leading-snug text-sm"
                    style={{ fontFamily: "'Lora', serif" }}
                  >
                    {r.name}
                  </p>

                  {/* Meal badge */}
                  <div className="mt-2">
                    <MealBadge type={r.mealType} />
                  </div>

                  {/* Availability label */}
                  {hasPantry && (
                    <div className="mt-2">
                      {r.tier === 1 ? <AvailableLabel /> : <AdditionalLabel />}
                    </div>
                  )}

                  {/* Match progress bar */}
                  {hasPantry && (
                    <div className="mt-3">
                      <div className="flex justify-between items-center mb-1">
                        <span
                          className="text-[9px] text-stone-400 uppercase tracking-wide"
                          style={{ fontFamily: "'DM Mono', monospace" }}
                        >
                          {RECIPE_CARD_LABELS.matchLabel}
                        </span>
                        <span
                          className="text-[9px] text-stone-500 font-semibold"
                          style={{ fontFamily: "'DM Mono', monospace" }}
                        >
                          {r.matched.length}/{r.coreIngredients.length}
                        </span>
                      </div>
                      <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
                        <motion.div
                          className={`h-full rounded-full ${
                            r.tier === 1 ? "bg-emerald-400" : "bg-orange-300"
                          }`}
                          initial={{ width: 0 }}
                          animate={{ width: `${r.score * 100}%` }}
                          transition={{
                            duration: 0.5,
                            ease: "easeOut",
                            delay: idx * 0.03,
                          }}
                        />
                      </div>
                      {r.missing.length > 0 && (
                        <p
                          className="text-[9px] text-orange-500 mt-1 truncate"
                          style={{ fontFamily: "'DM Mono', monospace" }}
                        >
                          Still need: {r.missing.slice(0, 3).join(", ")}
                          {r.missing.length > 3 ? "…" : ""}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.button>
          ))}
        </div>

        {ranked.length === 0 && (
          <div className="text-center py-16 text-stone-400">
            <p className="text-4xl mb-3">{EMPTY_STATE.icon}</p>
            <p
              className="font-semibold text-stone-500"
              style={{ fontFamily: "'Lora', serif" }}
            >
              {EMPTY_STATE.title}
            </p>
            <p
              className="text-sm mt-1"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              {EMPTY_STATE.body}
            </p>
          </div>
        )}
      </div>
    </div>
  );

  // ── Chat Panel JSX ─────────────────────────────────────────────────────────
  const chatPanel = (
    <div className="flex flex-col h-full min-h-0 bg-[#f9f6f1]">
      {/* Chat header */}
      <header className="flex-shrink-0 px-5 py-4 bg-white border-b border-stone-100 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-primary/10 border-2 border-primary/20 flex items-center justify-center">
            <ChefHat size={16} className="text-primary" />
          </div>
          <div>
            <p
              className="text-sm font-semibold text-stone-800"
              style={{ fontFamily: "'Lora', serif" }}
            >
              {CHAT_HEADER.name}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className={`w-1.5 h-1.5 rounded-full ${connectionStatus.dot} animate-pulse`} />
              <p
                className={`text-[9px] uppercase tracking-widest ${connectionStatus.text}`}
                style={{ fontFamily: "'DM Mono', monospace" }}
              >
                {isTyping ? (
                  <span className="text-primary">{CHAT_HEADER.statusThinking}</span>
                ) : (
                  connectionStatus.label
                )}
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <div
        className="flex-1 overflow-y-auto px-4 py-5 space-y-4 min-h-0"
        style={{
          scrollbarWidth: "thin",
          scrollbarColor: "#e5e0d5 transparent",
        }}
      >
        {messages.map((msg) => (
          <motion.div
            key={msg.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
            className={`flex items-end gap-2 ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            {msg.role === "assistant" && (
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center mb-0.5">
                <ChefHat size={12} className="text-primary" />
              </div>
            )}
            <div
              className={`max-w-[85%] px-4 py-3 text-sm leading-relaxed shadow-sm whitespace-pre-line ${
                msg.role === "user"
                  ? "bg-primary text-white rounded-2xl rounded-br-md shadow-primary/20"
                  : "bg-white text-stone-700 rounded-2xl rounded-bl-md border border-stone-100"
              }`}
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              {msg.content}
            </div>
          </motion.div>
        ))}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-end gap-2 justify-start"
          >
            <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
              <ChefHat size={12} className="text-primary" />
            </div>
            <div className="bg-white border border-stone-100 rounded-2xl rounded-bl-md shadow-sm">
              <TypingDots />
            </div>
          </motion.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quick prompts can be collapsed to give the chat more vertical space. */}
      <div className="flex-shrink-0 px-4 pb-2 space-y-1.5">
        <button
          onClick={() => setShowQuickPrompts((visible) => !visible)}
          className="w-full flex items-center justify-between text-[9px] text-stone-400 uppercase tracking-widest mb-1 px-0.5 hover:text-stone-600 transition-colors"
          style={{ fontFamily: "'DM Mono', monospace" }}
        >
          Quick questions:
          <ChevronDown
            size={12}
            className={`transition-transform ${showQuickPrompts ? "" : "-rotate-90"}`}
          />
        </button>
        {showQuickPrompts &&
          QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => sendMsg(prompt)}
              className="w-full text-left text-xs px-3.5 py-2 rounded-xl border border-stone-200 bg-white text-stone-500 hover:border-primary/40 hover:text-primary hover:bg-primary/5 transition-all shadow-sm"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            >
              {prompt}
            </button>
          ))}
      </div>

      {/* Chat input */}
      <div className="flex-shrink-0 px-4 pb-4 pt-2">
        <div className="flex items-end gap-2 bg-white border border-stone-200 rounded-2xl px-4 py-3 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/10 transition-all shadow-sm">
          <textarea
            ref={textareaRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleChatKey}
            placeholder={CHAT_INPUT_PLACEHOLDER}
            rows={1}
            className="flex-1 bg-transparent text-sm text-stone-800 placeholder:text-stone-300 resize-none outline-none leading-relaxed overflow-hidden"
            style={{
              scrollbarWidth: "none",
              minHeight: "24px",
              maxHeight: "120px",
              fontFamily: "'DM Sans', sans-serif",
            }}
          />
          <button
            onClick={() => sendMsg()}
            disabled={!chatInput.trim() || isTyping}
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-primary hover:bg-primary/90 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center transition-all active:scale-95 shadow-sm shadow-primary/25"
          >
            <Send size={14} className="text-white translate-x-px" />
          </button>
        </div>
        <p
          className="text-center text-[9px] text-stone-300 mt-1.5 tracking-wide"
          style={{ fontFamily: "'DM Mono', monospace" }}
        >
          {CHAT_INPUT_HINT}
        </p>
      </div>
    </div>
  );

  // ── Main Layout ────────────────────────────────────────────────────────────
  return (
    <div
      className="size-full flex flex-col overflow-hidden bg-[#f9f6f1]"
      style={{ fontFamily: "'DM Sans', sans-serif" }}
    >
      {/* Desktop (lg+) */}
      <div className="hidden lg:flex size-full overflow-hidden">
        <div className="flex-1 min-w-0 overflow-hidden border-r border-stone-200">
          {recipePanel}
        </div>
        <div className="w-[340px] xl:w-[380px] flex-shrink-0 overflow-hidden">
          {chatPanel}
        </div>
      </div>

      {/* Mobile / Tablet (<lg) */}
      <div className="flex lg:hidden flex-col size-full overflow-hidden">
        <div className="flex-shrink-0 flex bg-white border-b border-stone-200">
          {[
            { id: "recipes", label: MOBILE_TABS.recipes, icon: BookOpen },
            { id: "chat", label: MOBILE_TABS.chat, icon: MessageSquare },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMobileTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 py-3.5 text-sm font-bold uppercase tracking-wider transition-colors border-b-2 ${
                mobileTab === id
                  ? "text-primary border-primary"
                  : "text-stone-400 border-transparent"
              }`}
              style={{ fontFamily: "'DM Mono', monospace" }}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>
        <div className="flex-1 min-h-0 overflow-hidden">
          {mobileTab === "recipes" ? recipePanel : chatPanel}
        </div>
      </div>

      <AnimatePresence>
        {selected && (
          <RecipeModal
            r={selected}
            onClose={() => setSelected(null)}
            hasPantry={hasPantry}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
