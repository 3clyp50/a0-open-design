import { createStore } from "/js/AlpineStore.js";
import { callJsonApi } from "/js/api.js";
import { store as chats } from "/components/sidebar/chats/chats-store.js";
import { toastFrontendError } from "/components/notifications/notification-store.js";

export const store = createStore("openDesign", {
  tab: "new", busy: false, ready: false, projects: [], systems: [], templates: [],
  title: "", brief: "", system: "default", template: "dashboard", search: "", current: null, viewport: "100%",
  init() {},
  async api(action, values = {}) {
    return callJsonApi("/plugins/open_design/studio", { action, ...values });
  },
  async refresh() {
    this.busy = true;
    try {
      const status = await this.api("status");
      this.ready = status.ready;
      this.projects = status.projects;
      if (this.current) this.current = this.projects.find(project => project.id === this.current.id) || null;
      if (this.ready && !this.systems.length) {
        const [systems, templates] = await Promise.all([this.api("catalog"), this.api("catalog", { collection: "templates" })]);
        this.systems = systems.items.sort((left, right) => Number(right.id === "default") - Number(left.id === "default"));
        this.templates = templates.items;
      }
    } catch (error) { toastFrontendError(error.message, "OpenDesign"); }
    finally { this.busy = false; }
  },
  get filteredSystems() {
    const query = this.search.toLowerCase();
    return this.systems.filter(system => `${system.name} ${system.category || ""}`.toLowerCase().includes(query));
  },
  get canCreate() { return this.ready && !this.busy && this.title.trim() && this.brief.trim(); },
  view(project) { this.current = project; this.tab = "preview"; },
  url(project, download = false) {
    return `/api/plugins/open_design/artifact?id=${encodeURIComponent(project.id)}&v=${encodeURIComponent(project.artifact || "")}${download ? "&download=1" : ""}`;
  },
  async create() {
    if (!this.canCreate) return;
    this.busy = true;
    try {
      const result = await this.api("create", { title: this.title, brief: this.brief, system: this.system, template: this.template });
      this.current = result.project;
      this.projects.unshift(result.project);
      this.tab = "preview";
      this.title = "";
      this.brief = "";
      await this.start(result.project);
    } catch (error) { toastFrontendError(error.message, "OpenDesign"); }
    finally { this.busy = false; }
  },
  async start(project = this.current) {
    this.busy = true;
    try {
      const { message, context_id } = await this.api("handoff", { project_id: project.id });
      if (context_id) {
        await chats.selectChat(context_id);
        return;
      }
      const context = await chats.newChat();
      if (!context) throw new Error("Could not create the design chat.");
      const result = await callJsonApi("/message_async", { text: message, context, message_id: crypto.randomUUID() });
      if (result.model_not_configured) throw new Error("Select a model in Agent Zero, then choose Design with A0.");
      await this.api("attach_chat", { project_id: project.id, context_id: context });
    } catch (error) { toastFrontendError(error.message, "OpenDesign"); }
    finally { this.busy = false; }
  },
  cleanup() {},
});
