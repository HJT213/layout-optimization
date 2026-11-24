(() => {
  "use strict";
  const T = window.THREE;
  const COLORS = {
    床: "#779997", 衣柜: "#c9a67b", 书桌: "#ca9d69", 椅子: "#799385", 床头柜: "#b08c6d", 书架: "#a08064",
    淋浴区: "#8ac1c5", 马桶: "#e7e9df", 洗手台: "#a5abae", 洗衣机: "#b7c3be", 收纳柜: "#c4a886",
    水槽: "#77999d", 操作台: "#bd956a", 灶台: "#9faaa3", 冰箱: "#899c9e", 储物柜: "#bd9c77", 备餐车: "#9f9cbb",
    沙发: "#638f83", 茶几: "#bf9c78", 电视柜: "#aa8768", 单人椅: "#a79ab3", 边柜: "#c39c72",
  };
  const ZONE = "#df8b68", FUNCTION = "#ddbc68", WINDOW = "#387e87";
  const DEFAULT = { angle: 0.58, elevation: 0.75, zoom: 1 };
  const clamp = (n, a, b) => Math.max(a, Math.min(b, n));
  const position = (room, x, y) => [x - room.width / 2, room.height / 2 - y];
  const center = ([x0, y0, x1, y1]) => [(x0 + x1) / 2, (y0 + y1) / 2];

  function furnitureMesh(item) {
    const g = new T.Group();
    const [u, v] = [item.width, item.depth];
    const color = COLORS[item.name] || "#a09280";
    const pale = "#f1eee3", dark = "#394a47", wood = "#8b6d54";
    const face = color;
    const materials = {};
    let high = 0;
    function b(x, y, z, w, h, d, c = face, metalness = 0) {
      materials[c] ??= new T.MeshStandardMaterial({ color: c, metalness, roughness: 0.75 });
      const mesh = new T.Mesh(new T.BoxGeometry(w, h, d), materials[c]);
      mesh.position.set(x, y, z);
      mesh.castShadow = mesh.receiveShadow = true;
      g.add(mesh);
      high = Math.max(high, y + h / 2);
    }
    function legs(h, mat = wood) {
      const t = Math.min(.055, u * .1, v * .1);
      for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
        b(sx * (u / 2 - t), h / 2, sz * (v / 2 - t), t, h, t, mat);
      }
    }
    function cabinet(h, top = pale) {
      b(0, h / 2, 0, u, h, v);
      b(0, h + .017, 0, u, .034, v, top);
      b(u * .22, h * .73, v / 2 - .005, u * .22, .027, .018, wood);
    }
    function stool(wide = false) {
      const h = wide ? .42 : .45;
      const t = wide ? .15 : .085;
      legs(h - t / 2);
      b(0, h, .03, u * .93, t, v * .88);
      b(0, h + .18, -v / 2 + .07, u, .44, .14);
      if (wide) for (const side of [-1, 1]) b(side * (u * .44), h + .11, .025, u * .12, .18, v * .8);
      if (wide && u > 1.2) b(0, h + t / 2, .035, .012, .012, v * .82, "#54766e");
    }
    switch (item.name) {
      case "床":
        b(0, .19, 0, u, .24, v, wood);
        b(0, .385, 0, u * .98, .17, v * .98, pale);
        b(0, .43, -v * .465, u, .80, v * .07, wood);
        b(0, .49, v * .16, u * .99, .06, v * .65);
        for (const side of [-1, 1]) b(side * u * .235, .505, -v * .27, u * .40, .075, v * .18, "#fbfaf2");
        break;
      case "沙发": case "单人椅": stool(true); break;
      case "椅子": stool(); break;
      case "书桌": case "茶几": case "备餐车": {
        const h = item.name === "茶几" ? .40 : .72;
        legs(h);
        b(0, h, 0, u, .065, v);
        if (item.name === "书桌") {
          b(-u * .22, h + .04, -v * .2, u * .26, .018, v * .43, "#a9b5ac");
          b(u * .12, h + .08, -v * .18, u * .17, .04, v * .26, "#eae2cf");
        }
        if (item.name === "备餐车") b(0, .25, 0, u * .93, .04, v * .93, pale);
        break;
      }
      case "书架":
        for (const side of [-1, 1]) b(side * (u / 2 - .022), .69, 0, .044, 1.38, v);
        b(0, .69, -v / 2 + .016, u, 1.38, .032, "#a58a6d");
        for (let i = 0; i < 4; i++) {
          b(0, .075 + i * .42, 0, u, .04, v);
          if (i < 3) for (let j = 0; j < 4; j++) {
            b((j - 1.7) * u / 7, .18 + i * .42, -.012, u / 9, .14 + (j % 2) * .056, v * .59, [pale, "#6d9385", "#bf9770", "#a79ab3"][j]);
          }
        }
        break;
      case "衣柜": case "冰箱": {
        const h = item.name === "衣柜" ? 1.79 : 1.64;
        b(0, h / 2, 0, u, h, v);
        if (item.name === "衣柜") {
          b(0, h / 2, v / 2 - .004, .012, h * .94, .015, wood);
          for (const side of [-1, 1]) b(side * u * .055, .88, v / 2 - .002, .022, .17, .023, wood);
        } else {
          b(0, h * .64, v / 2 - .005, u * .98, .025, .014, dark);
          for (const y of [.79, 1.16]) b(-u * .32, y, v / 2 - .003, .038, .15, .027, pale);
        }
        break;
      }
      case "电视柜":
        cabinet(.35, "#d1b28d");
        b(0, .415, 0, u * .33, .06, v * .48, dark);
        b(0, .69, -.035, u * .81, .50, .06, dark);
        b(0, .69, -.001, u * .76, .45, .012, "#657e7b");
        break;
      case "水槽": case "洗手台":
        cabinet(.81);
        b(0, .851, -.025, u * .65, .022, v * .55, "#546e6f", .45);
        b(0, .863, -.025, u * .52, .022, v * .43, "#9bb3b3", .34);
        b(0, .97, -v * .37, .035, .23, .037, "#9daea9", .50);
        b(0, 1.06, -v * .27, .035, .03, v * .25, "#9daea9", .50);
        break;
      case "灶台":
        cabinet(.81);
        b(0, .855, 0, u * .82, .025, v * .78, dark);
        for (const x of [-.21, .21]) for (const z of [-.20, .20]) {
          const burner = new T.Mesh(new T.CylinderGeometry(Math.min(u, v) * .125, Math.min(u, v) * .125, .023, 20),
            new T.MeshStandardMaterial({ color: "#768784", roughness: .7 }));
          burner.position.set(x * u, .877, z * v);
          g.add(burner);
        }
        break;
      case "操作台": cabinet(.81); break;
      case "淋浴区": {
        b(0, .04, 0, u, .08, v, "#a7c8c6");
        const glass = new T.Mesh(new T.BoxGeometry(.038, .84, v * .75),
          new T.MeshStandardMaterial({ color: "#8cd4d5", transparent: true, opacity: .46, depthWrite: false }));
        glass.position.set(u / 2 - .024, .50, -v * .105);
        g.add(glass);
        b(u / 2 - .024, .92, -v * .105, .044, .03, v * .76, "#7ca5a5");
        break;
      }
      case "洗衣机": {
        b(0, .42, 0, u, .84, v);
        const round = new T.Mesh(new T.CylinderGeometry(u * .31, u * .31, .025, 22), new T.MeshStandardMaterial({ color: "#475b5d" }));
        round.rotateX(Math.PI / 2);
        round.position.set(0, .40, v / 2);
        g.add(round);
        b(-u * .22, .73, v / 2, u * .22, .04, .025, pale);
        break;
      }
      case "马桶":
        b(0, .32, -v * .34, u * .87, .60, v * .28, pale);
        b(0, .15, v * .05, u * .64, .30, v * .47, pale);
        b(0, .34, v * .10, u * .82, .095, v * .66, "#fbfaf4");
        break;
      case "床头柜": cabinet(.48); break;
      case "收纳柜": cabinet(.76); break;
      case "边柜": cabinet(.66); break;
      default: cabinet(.83);
    }
    const direction = item.front_xy || (item.rotation_deg === 90 ? [1, 0] : [0, -1]);
    g.rotation.y = Math.atan2(direction[0], -direction[1]);
    return { g, high };
  }

  function makeScene(room, result) {
    const scene = new T.Scene();
    const outlineMaterials = new Map();
    const materials = new Map();
    const groups = { walls: {}, zones: new T.Group(), labels: [] };
    function solid(group, x, y, z, w, h, d, color, options = {}) {
      if (Math.min(w, h, d) <= .0001) return;
      const key = color + JSON.stringify(options);
      if (!materials.has(key)) materials.set(key, new T.MeshStandardMaterial({ color, roughness: .92, ...options }));
      const mesh = new T.Mesh(new T.BoxGeometry(w, h, d), materials.get(key));
      mesh.position.set(x, y, z);
      mesh.receiveShadow = !options.transparent;
      mesh.castShadow = !options.transparent;
      group.add(mesh);
      return mesh;
    }
    function outline(group, points, color) {
      if (!outlineMaterials.has(color)) outlineMaterials.set(color, new T.LineBasicMaterial({ color }));
      group.add(new T.LineLoop(new T.BufferGeometry().setFromPoints(points.map(p => new T.Vector3(...p))), outlineMaterials.get(color)));
    }
    const { width: w, height: d } = room;
    const floor = solid(scene, 0, -.085, 0, w + .16, .17, d + .16, "#e4ddc8");
    floor.castShadow = false;
    const gridVerts = [];
    for (let x = .5; x < w - .01; x += .5) gridVerts.push(...position(room, x, 0), ...position(room, x, d));
    for (let y = .5; y < d - .01; y += .5) gridVerts.push(...position(room, 0, y), ...position(room, w, y));
    const gridData = [];
    for (let i = 0; i < gridVerts.length; i += 2) gridData.push(gridVerts[i], .002, gridVerts[i + 1]);
    const gridGeo = new T.BufferGeometry();
    gridGeo.setAttribute("position", new T.Float32BufferAttribute(gridData, 3));
    scene.add(new T.LineSegments(gridGeo, new T.LineBasicMaterial({ color: "#b7b09d", transparent: true, opacity: .60 })));

    const walls = [
      { id: "door", axis: 0, at: d / 2, length: w, normal: [0, 1] },
      { id: "opposite", axis: 0, at: -d / 2, length: w, normal: [0, -1] },
      { id: "left", axis: 1, at: -w / 2, length: d, normal: [-1, 0] },
      { id: "right", axis: 1, at: w / 2, length: d, normal: [1, 0] },
    ];
    const windowWall = result.window?.wall;
    const wallColor = "#cfdbd3", trimColor = "#9aada1", wallHeight = 1.90, sill = .90, lintel = 1.64;
    for (const wall of walls) {
      const full = new T.Group(), cut = new T.Group();
      scene.add(full, cut);
      groups.walls[wall.id] = { full, cut, normal: wall.normal };
      const edge = wall.length / 2;
      const block = (dest, a, b, bottom, top, color = wallColor, thickness = .105, opt) => {
        if (b - a < .0001) return;
        const along = (a + b) / 2;
        const [x, z] = wall.axis === 0 ? [along, wall.at] : [wall.at, along];
        solid(dest, x, (bottom + top) / 2, z, wall.axis === 0 ? b - a : thickness, top - bottom, wall.axis === 0 ? thickness : b - a, color, opt);
      };
      if (wall.id === windowWall) {
        const [a, b] = result.window.endpoints_m.map(([x, y]) => position(room, x, y)[wall.axis]).sort((l, r) => l - r);
        block(full, -edge, a, 0, wallHeight);
        block(full, b, edge, 0, wallHeight);
        block(full, a, b, 0, sill);
        block(full, a, b, lintel, wallHeight);
        block(full, a, b, sill, sill + .036, WINDOW, .129);
        block(full, a, b, lintel - .035, lintel, WINDOW, .129);
        block(full, a, a + .033, sill, lintel, WINDOW, .129);
        block(full, b - .033, b, sill, lintel, WINDOW, .129);
        block(full, (a + b) / 2 - .014, (a + b) / 2 + .014, sill, lintel, WINDOW, .107);
        block(full, a, b, sill, lintel, "#7fc9d1", .021, { transparent: true, opacity: .33, depthWrite: false });
        block(cut, -edge, edge, 0, .13, trimColor);
        block(cut, a, b, .13, .19, WINDOW, .135);
      } else if (wall.id === "door" && room.zones[0]) {
        const a = room.zones[0][0] - w / 2, b = room.zones[0][2] - w / 2;
        block(full, -edge, a, 0, wallHeight);
        block(full, b, edge, 0, wallHeight);
        block(cut, -edge, a, 0, .13, trimColor);
        block(cut, b, edge, 0, .13, trimColor);
        block(scene, a, b, .002, .02, "#956649", .126);
      } else {
        block(full, -edge, edge, 0, wallHeight);
        block(cut, -edge, edge, 0, .13, trimColor);
      }
    }

    function area(box, color, i) {
      const [x0, y0, x1, y1] = box, [x, z] = position(room, ...center(box)), y = .009 + i * .003;
      solid(groups.zones, x, y, z, x1 - x0, .004, y1 - y0, color, { transparent: true, opacity: .37, depthWrite: false });
      outline(groups.zones, [[x0,y0],[x1,y0],[x1,y1],[x0,y1]].map(([x,y2]) => {
        const [px,pz] = position(room,x,y2);
        return [px, y + .006, pz];
      }), color);
    }
    room.zones.forEach((box, i) => area(box, ZONE, i));
    if (result.functional_zone) area(result.functional_zone, FUNCTION, 2);
    scene.add(groups.zones);

    for (const item of result.furniture) {
      const { g, high } = furnitureMesh(item);
      const [x, z] = position(room, ...center(item.box_m));
      g.position.set(x, 0, z);
      scene.add(g);
      groups.labels.push({ name: item.name, point: new T.Vector3(x, high + .09, z) });
    }
    const sky = new T.HemisphereLight("#fffaf0", "#a7b6ad", 2.15);
    const sun = new T.DirectionalLight("#fff4df", 2.1);
    sun.position.set(-3.4, 6.8, 4.3);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    Object.assign(sun.shadow.camera, { left: -5.0, right: 5.0, bottom: -5.0, top: 5.0, near: 1, far: 18 });
    sun.shadow.normalBias = .022;
    sun.shadow.bias = -.00035;
    scene.add(sky, sun);
    return { scene, ...groups };
  }

  function disposeScene(scene) {
    if (!scene) return;
    const resources = new Set();
    scene.traverse(object => {
      if (object.geometry) resources.add(object.geometry);
      if (object.material) resources.add(object.material);
      if (object.shadow) resources.add(object.shadow);
    });
    resources.forEach(resource => resource.dispose());
  }

  function createView(host) {
    const flat = document.createElement("canvas");
    flat.setAttribute("aria-hidden", "true");
    host.append(flat);
    let renderer = null;
    if (T) try {
      renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setClearColor(0, 0);
      renderer.outputColorSpace = T.SRGBColorSpace;
      renderer.toneMapping = T.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.05;
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = T.PCFSoftShadowMap;
      renderer.domElement.setAttribute("aria-hidden", "true");
      host.append(renderer.domElement);
    } catch { renderer = null; }
    const layer = document.createElement("div");
    layer.className = "scene-labels";
    layer.setAttribute("aria-hidden", "true");
    host.append(layer);
    return { host, flat, renderer, layer, model: null, result: null, labelNodes: [], size: "", camera: renderer ? new T.OrthographicCamera(-1, 1, 1, -1, .01, 60) : null };
  }

  function drawFlat(view, room, settings, w, h, pixelRatio) {
    const canvas = view.flat;
    if (canvas.width !== Math.round(w * pixelRatio) || canvas.height !== Math.round(h * pixelRatio)) {
      canvas.width = Math.round(w * pixelRatio);
      canvas.height = Math.round(h * pixelRatio);
    }
    const ctx = canvas.getContext("2d");
    const pad = Math.min(27, w * .10);
    const scale = Math.min((w - pad * 2) / room.width, (h - pad * 2) / room.height);
    const x0 = (w - room.width * scale) / 2, y0 = (h - room.height * scale) / 2;
    const proj = ([x,y]) => [x0 + x * scale, y0 + (room.height - y) * scale];
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    ctx.clearRect(0, 0, w, h);
    function rect([x,y,a,b], fill, stroke, line = 1) {
      const [px,py] = proj([x,b]), rw = (a-x)*scale, rh = (b-y)*scale;
      ctx.fillStyle = fill;
      ctx.fillRect(px, py, rw, rh);
      ctx.strokeStyle = stroke;
      ctx.lineWidth = line;
      ctx.strokeRect(px, py, rw, rh);
    }
    function line(a,b,color,width) {
      ctx.beginPath();
      ctx.moveTo(...proj(a)); ctx.lineTo(...proj(b));
      ctx.lineWidth = width; ctx.strokeStyle = color; ctx.stroke();
    }
    rect([0,0,room.width,room.height], "#f2eee2", "#71847a", 2);
    for (let x = .5; x < room.width; x += .5) line([x,0], [x,room.height], "#dbd5c7", .7);
    for (let y = .5; y < room.height; y += .5) line([0,y], [room.width,y], "#dbd5c7", .7);
    if (settings.zones) {
      room.zones.forEach(box => rect(box, "#edac8e80", ZONE));
      if (view.result.functional_zone) rect(view.result.functional_zone, "#edcd7780", FUNCTION);
    }
    if (room.zones[0]) line([room.zones[0][0],0], [room.zones[0][2],0], "#a16c51", 4);
    if (view.result.window) line(...view.result.window.endpoints_m, WINDOW, 4);
    for (const item of view.result.furniture) {
      rect(item.box_m, COLORS[item.name] || "#a09280", "#5e6c66");
      if (settings.labels) {
        const [x,y] = proj(center(item.box_m));
        ctx.fillStyle = "#182621";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.font = (w < 250 ? "9" : "12") + "px Microsoft YaHei, sans-serif";
        ctx.fillText(item.name, x, y);
      }
    }
  }

  window.createRoomComparison = function (hosts, onFallback) {
    const views = hosts.map(createView);
    let available = views.every(view => view.renderer);
    const settings = { ...DEFAULT, mode: available ? "3d" : "2d", labels: false, zones: true };
    let room = null, queued = false;
    function contextLost(event) {
      event.preventDefault();
      available = false;
      settings.mode = "2d";
      onFallback?.();
      schedule();
    }
    for (const view of views) view.renderer?.domElement.addEventListener("webglcontextlost", contextLost);
    function schedule() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => { queued = false; draw(); });
    }
    function draw() {
      if (!room) return;
      for (const view of views) {
        const w = view.host.clientWidth, h = view.host.clientHeight, pixelRatio = Math.min(devicePixelRatio || 1, 1.75);
        if (!w || !h) continue;
        const is3d = available && settings.mode === "3d";
        view.host.classList.toggle("flat", !is3d);
        view.flat.hidden = is3d;
        if (view.renderer) view.renderer.domElement.hidden = !is3d;
        view.layer.hidden = !is3d || !settings.labels;
        if (!is3d) {
          drawFlat(view, room, settings, w, h, pixelRatio);
          continue;
        }
        const { renderer, camera, model } = view;
        if (view.size !== [w,h,pixelRatio].join(",")) {
          renderer.setPixelRatio(pixelRatio);
          renderer.setSize(w, h, false);
          view.size = [w,h,pixelRatio].join(",");
        }
        const { angle, elevation, zoom } = settings;
        const [dx, dz] = [Math.sin(angle), Math.cos(angle)];
        const ground = Math.cos(elevation), target = new T.Vector3(0, .55, 0);
        camera.position.set(dx * ground * 12, target.y + Math.sin(elevation) * 12, dz * ground * 12);
        camera.lookAt(target);
        camera.updateMatrixWorld();
        for (const { full, cut, normal } of Object.values(model.walls)) {
          full.visible = dx * normal[0] + dz * normal[1] < .12;
          cut.visible = !full.visible;
        }
        model.zones.visible = settings.zones;
        // Fit both panels to the same room envelope, independent of furniture positions.
        let left = Infinity, right = -Infinity, low = Infinity, high = -Infinity;
        const local = new T.Vector3();
        for (const x of [-(room.width / 2 + .09), room.width / 2 + .09])
          for (const y of [-.17, 1.90])
            for (const z of [-(room.height / 2 + .09), room.height / 2 + .09]) {
              local.set(x, y, z).applyMatrix4(camera.matrixWorldInverse);
              left = Math.min(left, local.x); right = Math.max(right, local.x);
              low = Math.min(low, local.y); high = Math.max(high, local.y);
            }
        const aspect = w / h;
        const cx = (right + left) / 2, cy = (high + low) / 2;
        const half = Math.max((high - low) / 2, (right - left) / (2 * aspect)) * 1.12 / zoom;
        camera.top = cy + half; camera.bottom = cy - half;
        camera.left = cx - half * aspect; camera.right = cx + half * aspect;
        camera.updateProjectionMatrix();
        renderer.render(model.scene, camera);
        if (settings.labels) model.labels.forEach(({point}, i) => {
          local.copy(point).project(camera);
          view.labelNodes[i].style.left = ((local.x + 1) * 50) + "%";
          view.labelNodes[i].style.top = ((1 - local.y) * 50) + "%";
        });
      }
    }
    for (const { host } of views) {
      const pointers = new Map();
      host.addEventListener("pointerdown", event => {
        if (settings.mode !== "3d" || (event.pointerType === "mouse" && event.button !== 0)) return;
        pointers.set(event.pointerId, [event.clientX, event.clientY]);
        host.setPointerCapture(event.pointerId);
        host.classList.add("is-dragging");
      });
      host.addEventListener("pointermove", event => {
        const old = pointers.get(event.pointerId);
        if (!old || settings.mode !== "3d") return;
        const next = [event.clientX, event.clientY];
        const other = [...pointers.entries()].find(([id]) => id !== event.pointerId)?.[1];
        if (other) {
          const dist = point => Math.hypot(point[0] - other[0], point[1] - other[1]);
          settings.zoom = clamp(settings.zoom * dist(next) / Math.max(1, dist(old)), .68, 2.15);
        } else {
          settings.angle -= (next[0] - old[0]) * .012;
          settings.elevation = clamp(settings.elevation + (next[1] - old[1]) * .009, .31, 1.45);
        }
        pointers.set(event.pointerId, next);
        schedule();
      });
      for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) host.addEventListener(type, event => {
        pointers.delete(event.pointerId);
        if (!pointers.size) host.classList.remove("is-dragging");
      });
      host.addEventListener("wheel", event => {
        if (settings.mode !== "3d") return;
        event.preventDefault();
        settings.zoom = clamp(settings.zoom * Math.exp(-event.deltaY * .0011), .68, 2.15);
        schedule();
      }, { passive: false });
      host.addEventListener("keydown", event => {
        if (settings.mode !== "3d") return;
        switch (event.key) {
          case "ArrowLeft": settings.angle -= .15; break;
          case "ArrowRight": settings.angle += .15; break;
          case "ArrowUp": settings.elevation = clamp(settings.elevation + .12, .31, 1.45); break;
          case "ArrowDown": settings.elevation = clamp(settings.elevation - .12, .31, 1.45); break;
          case "+": case "=": settings.zoom = clamp(settings.zoom * 1.1, .68, 2.15); break;
          case "-": settings.zoom = clamp(settings.zoom / 1.1, .68, 2.15); break;
          default: return;
        }
        event.preventDefault();
        schedule();
      });
    }
    const observer = new ResizeObserver(schedule);
    views.forEach(view => observer.observe(view.host));
    return {
      get available() { return available; },
      update(nextRoom, results) {
        room = nextRoom;
        views.forEach((view, i) => {
          disposeScene(view.model?.scene);
          view.result = results[i];
          view.model = available ? makeScene(room, view.result) : null;
          view.labelNodes = (view.model?.labels || []).map(({name}) => {
            const node = document.createElement("span");
            node.className = "scene-label";
            node.textContent = name;
            return node;
          });
          view.layer.replaceChildren(...view.labelNodes);
        });
        schedule();
      },
      set(key, value) { settings[key] = value; schedule(); },
      reset() { Object.assign(settings, DEFAULT); schedule(); },
    };
  };
})();
