(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const data = window.LAYOUT_DATA;
  const svgNS = "http://www.w3.org/2000/svg";
  const number = new Intl.NumberFormat("zh-CN");
  const types = {
    bedroom: ["卧室", "bed-double"], bathroom: ["卫生间", "bath"],
    kitchen: ["厨房", "cooking-pot"], living: ["客厅", "sofa"],
  };
  const methods = {
    ga: { name: "遗传算法", color: "#216452", dash: "" },
    random: { name: "随机搜索", color: "#ab572b", dash: "5 4" },
    ga_no_mutation: { name: "无变异遗传算法", color: "#655799", dash: "2 3" },
  };
  const state = { type: "kitchen", size: "compact", method: "ga", seed: 20, labels: false, zones: true, mode: "3d" };

  function svgNode(name, attrs, content) {
    const node = document.createElementNS(svgNS, name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (content !== undefined) node.textContent = content;
    return node;
  }

  function addIcons() {
    document.querySelectorAll("[data-icon]").forEach(node => {
      const paths = window.LAYOUT_ICONS?.[node.dataset.icon];
      if (!paths) return;
      const svg = svgNode("svg", {
        viewBox: "0 0 24 24", "aria-hidden": "true", "data-lucide": node.dataset.icon,
        fill: "none", stroke: "currentColor", "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round",
      });
      svg.append(...paths.map(([name, attrs]) => svgNode(name, attrs)));
      node.replaceChildren(svg);
    });
  }

  for (const [type, [name, icon]] of Object.entries(types)) {
    const button = document.createElement("button");
    const mark = document.createElement("span");
    mark.dataset.icon = icon;
    button.type = "button";
    button.dataset.type = type;
    button.append(mark, name);
    button.addEventListener("click", () => { state.type = type; render(); });
    $("roomTypes").append(button);
  }
  $("roomSizes").querySelectorAll("button").forEach(button => {
    button.addEventListener("click", () => { state.size = button.dataset.size; render(); });
  });
  $("methodSelect").addEventListener("change", event => { state.method = event.target.value; render(); });
  $("seedSelect").append(...data.displaySeeds.map(seed => new Option(String(seed), String(seed))));
  $("seedSelect").addEventListener("change", event => { state.seed = Number(event.target.value); render(); });
  $("runTotal").textContent = number.format(data.totalRuns);
  addIcons();

  const comparison = window.createRoomComparison([$("initialView"), $("bestView")], () => setMode("2d"));
  function setMode(mode) {
    state.mode = comparison.available ? mode : "2d";
    comparison.set("mode", state.mode);
    $("mode3d").disabled = !comparison.available;
    $("resetCamera").disabled = state.mode === "2d";
    $("mode3d").setAttribute("aria-pressed", state.mode === "3d");
    $("mode2d").setAttribute("aria-pressed", state.mode === "2d");
    $("cameraHint").textContent = state.mode === "3d" ? "同步视角 · 拖动旋转，滚轮缩放" : "同尺度平面图";
    $("viewNote").textContent = !comparison.available ? "当前浏览器使用平面视图" : state.mode === "3d" ? "3D 高度为展示设定" : "坐标单位为米";
  }
  setMode("3d");
  $("mode3d").addEventListener("click", () => setMode("3d"));
  $("mode2d").addEventListener("click", () => setMode("2d"));
  $("resetCamera").addEventListener("click", () => comparison.reset());
  for (const [id, key] of [["toggleLabels", "labels"], ["toggleZones", "zones"]]) {
    $(id).addEventListener("click", () => {
      state[key] = !state[key];
      $(id).setAttribute("aria-pressed", state[key]);
      comparison.set(key, state[key]);
    });
  }
  document.querySelectorAll(".topinner nav a").forEach(link => link.addEventListener("click", () => {
    document.querySelectorAll(".topinner nav a").forEach(item => item.classList.toggle("active", item === link));
  }));

  function status(prefix, { feasible, cost, violation_m2 }) {
    const badge = $(prefix + "Status");
    badge.classList.toggle("good", feasible);
    badge.textContent = feasible ? "满足约束" : "未满足约束";
    $(prefix + "Cost").textContent = cost > 0 && cost < .0001 ? cost.toExponential(2) : cost.toFixed(4);
    $(prefix + "Violation").textContent = area(violation_m2) + " m²";
  }

  function area(value) {
    if (value == null) return "—";
    if (value <= 1e-9) return "0";
    return value < .001 ? value.toExponential(2) : value.toFixed(3);
  }

  function renderStats(room, initial, best) {
    $("statsBars").replaceChildren(...data.methods.map(key => {
      const { feasible, total } = room.stats[key], { name, color } = methods[key];
      const row = document.createElement("div");
      row.className = "bar-row";
      const label = document.createElement("span");
      label.textContent = name;
      const track = document.createElement("div");
      track.className = "track";
      track.setAttribute("aria-hidden", "true");
      const bar = document.createElement("i");
      bar.style.cssText = "--series:" + color + ";width:" + (100 * feasible / total) + "%";
      track.append(bar);
      const figure = document.createElement("strong");
      figure.textContent = feasible + " / " + total;
      row.append(label, track, figure);
      return row;
    }));
    const checkKeys = [["家具重叠", "overlap_m2"], ["门前区占用", "door_m2"], ["通道占用", "passage_m2"]];
    if (initial.clearance_m2 != null) checkKeys.push([room.kind === "kitchen" ? "操作净空占用" : "绕行区占用", "clearance_m2"]);
    $("checksBody").replaceChildren(...checkKeys.map(([name, key]) => {
      const row = document.createElement("tr");
      for (const value of [name, area(initial[key]), area(best[key])]) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }));
  }

  let currentExample;
  function renderChart() {
    if (!currentExample) return;
    const series = currentExample.methods;
    const chart = $("curve"), width = Math.max(chart.clientWidth, 250), height = 245;
    const x0 = 58, x1 = width - 15, y0 = 24, y1 = height - 37;
    const costs = Object.values(series).flatMap(value => value.cost);
    const minPositive = Math.min(...costs.filter(value => value > 0));
    const logFloor = Number.isFinite(minPositive) ? minPositive / 2 : 1e-8;
    const log = value => Math.log10(Math.max(logFloor, value));
    const low = Math.floor(log(Math.min(...costs))), high = Math.max(low + 1, Math.ceil(log(Math.max(...costs))));
    const x = i => x0 + (x1 - x0) * i / data.config.generations;
    const y = cost => y1 - (y1 - y0) * (log(cost) - low) / (high - low);
    const line = (xa, ya, xb, yb, stroke = "#dfe5df") => svgNode("line", { x1: xa, y1: ya, x2: xb, y2: yb, stroke });
    const text = (px, py, label, anchor = "start") => svgNode("text", { x: px, y: py, fill: "currentColor", "text-anchor": anchor }, label);
    chart.setAttribute("viewBox", [0, 0, width, height].join(" "));
    const nodes = [text(2, 11, "总成本 · 对数刻度")];
    const step = Math.max(1, Math.ceil((high - low) / 6));
    for (let power = low; power <= high; power += step) {
      const yy = y1 - (y1 - y0) * (power - low) / (high - low);
      nodes.push(line(x0, yy, x1, yy), text(x0 - 5, yy + 4, power >= -3 && power <= 3 ? String(10 ** power) : "1e" + power, "end"));
    }
    for (let i = 0; i <= 4; i++) {
      const value = Math.round(data.config.generations * i / 4), xx = x(value);
      nodes.push(line(xx, y0, xx, y1), text(xx, y1 + 16, String(value), "middle"));
    }
    nodes.push(line(x0, y0, x0, y1, "#98a99f"), line(x0, y1, x1, y1, "#98a99f"),
      text((x0 + x1) / 2, height - 3, "迭代轮次", "middle"));
    const order = data.methods.filter(method => method !== state.method).concat(state.method);
    for (const key of order) {
      const { color, dash, name } = methods[key];
      const points = series[key].cost.map((cost, i) => x(i).toFixed(2) + "," + y(cost).toFixed(2));
      const curve = svgNode("polyline", {
        points: points.join(" "), fill: "none", stroke: color, "stroke-width": key === state.method ? 2.6 : 1.6,
        "stroke-dasharray": dash, "stroke-linejoin": "round",
      });
      curve.append(svgNode("title", {}, name + " · 最终成本 " + series[key].best.metrics.cost.toPrecision(4)));
      nodes.push(curve);
    }
    chart.replaceChildren(...nodes);
  }
  $("curveKey").replaceChildren(...data.methods.map(key => {
    const { name, color, dash } = methods[key], item = document.createElement("span");
    item.classList.toggle("dash", Boolean(dash));
    item.style.setProperty("--series", color);
    item.append(document.createElement("i"), name);
    return item;
  }));
  new ResizeObserver(renderChart).observe($("curve"));

  function render() {
    const key = state.type === "bedroom" ? state.size : state.type + "_" + state.size;
    const room = data.rooms[key];
    currentExample = room.examples[state.seed];
    const { initial } = currentExample;
    const run = currentExample.methods[state.method], { best } = run;
    const dimensions = room.width.toFixed(2) + " × " + room.height.toFixed(2) + " m";
    $("roomTitle").textContent = room.title;
    $("roomDimensions").textContent = dimensions + " · " + (room.width * room.height).toFixed(2) + " m²";
    $("functionalLegend").hidden = !room.functional;
    $("functionalName").textContent = room.kind === "living" ? "绕行区" : "操作净空";
    $("roomTypes").querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", button.dataset.type === state.type));
    $("roomSizes").querySelectorAll("button").forEach(button => button.setAttribute("aria-pressed", button.dataset.size === state.size));
    status("initial", initial.metrics);
    status("best", best.metrics);
    $("budget").textContent = "每次运行 " + number.format(run.evaluations) + " 次候选评估";
    $("chartSeed").textContent = "种子 " + state.seed;
    renderStats(room, initial.metrics, best.metrics);
    renderChart();
    comparison.update(room, [initial, best]);
  }
  render();
})();
