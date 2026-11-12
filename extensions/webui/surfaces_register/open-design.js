export default function register(surfaces) {
  surfaces.registerSurface({ id: "open_design", title: "OpenDesign", icon: "draw", order: 61,
    modalPath: "/plugins/open_design/webui/main.html", open() {}, close() {} });
}
