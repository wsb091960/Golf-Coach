(() => {
  "use strict";
  const form = document.getElementById("flight-input-form");
  if (!form || !document.getElementById("wi-apply")) return;
  const ids = ["pelvis", "torso", "spine", "arms"];
  const slider = id => document.getElementById("wi-" + id);
  const val = id => Number(slider(id).value);
  const num = name => Number(form.elements.namedItem(name).value) || 0;
  const base = { path: num("club_path"), face: num("club_face") };
  const signed = n => (n > 0 ? "+" : "") + n.toFixed(1) + "°";
  let prediction = null;
  function predict() {
    const p = val("pelvis"), t = val("torso"), s = val("spine"), a = val("arms");
    // Hypothetical illustrative sensitivities only; NOT fitted to swing data.
    const pathDelta = -0.10*p - 0.06*t + 0.025*s + 0.12*a;
    const faceDelta = -0.025*p - 0.035*t + 0.075*a;
    return {path: base.path + pathDelta, face: base.face + faceDelta, pathDelta, faceDelta};
  }
  function render() {
    ids.forEach(id => document.getElementById("wi-" + id + "-out").textContent = val(id) + "°");
    prediction = predict();
    const values = {"wi-path":prediction.path,"wi-face":prediction.face,"wi-f2p":prediction.face-prediction.path,"wi-path-delta":prediction.pathDelta,"wi-face-delta":prediction.faceDelta};
    Object.entries(values).forEach(([id,n]) => document.getElementById(id).textContent = signed(n));
    compare();
  }
  function compare() {
    const pathInput = document.getElementById("wi-actual-path").value;
    const faceInput = document.getElementById("wi-actual-face").value;
    const el = document.getElementById("wi-comparison");
    if (pathInput === "" || faceInput === "") {
      el.textContent = "Enter measured results after testing to compare against the estimate.";
      return;
    }
    const actualPath = Number(pathInput), actualFace = Number(faceInput);
    el.textContent = "Path error (actual − estimated): " + signed(actualPath-prediction.path)
      + " · Face error: " + signed(actualFace-prediction.face)
      + " · Actual face-to-path: " + signed(actualFace-actualPath);
  }
  ids.forEach(id => slider(id).addEventListener("input", render));
  ["wi-actual-path","wi-actual-face"].forEach(id => document.getElementById(id).addEventListener("input", compare));
  document.getElementById("wi-reset").addEventListener("click", () => {
    ids.forEach(id => slider(id).value = 0);
    render();
  });
  document.getElementById("wi-apply").addEventListener("click", () => {
    render();
    form.elements.namedItem("club_path").value = prediction.path.toFixed(2);
    form.elements.namedItem("club_face").value = prediction.face.toFixed(2);
    // The existing simulator computes face-to-path, spin axis and redraws the flight.
    form.dispatchEvent(new Event("submit", {bubbles:true,cancelable:true}));
    document.getElementById("standalone-flight-canvas").scrollIntoView({behavior:"smooth",block:"center"});
  });
  render();
})();