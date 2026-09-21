(function(){
  "use strict";
  var navs=Array.prototype.slice.call(document.querySelectorAll("[data-workspace-tabs]"));
  function activate(nav,name,focus){
    var group=nav.dataset.workspaceTabs;
    var buttons=Array.prototype.slice.call(nav.querySelectorAll("[data-workspace-tab]"));
    var selected=buttons.find(function(button){return button.dataset.workspaceTab===name;});
    if(!selected)return;
    buttons.forEach(function(button){
      var active=button===selected;
      button.setAttribute("aria-selected",active?"true":"false");
      button.setAttribute("tabindex",active?"0":"-1");
    });
    document.querySelectorAll('[data-workspace-panel][data-workspace-group="'+group+'"]').forEach(function(panel){
      panel.hidden=panel.dataset.workspacePanel!==name;
    });
    window.setTimeout(function(){window.dispatchEvent(new Event("resize"));},0);
    if(focus)selected.focus();
  }
  navs.forEach(function(nav){
    var buttons=Array.prototype.slice.call(nav.querySelectorAll("[data-workspace-tab]"));
    buttons.forEach(function(button,index){
      button.addEventListener("click",function(){activate(nav,button.dataset.workspaceTab,false);});
      button.addEventListener("keydown",function(event){
        if(event.key!=="ArrowLeft"&&event.key!=="ArrowRight")return;
        event.preventDefault();
        var direction=event.key==="ArrowRight"?1:-1;
        var next=(index+direction+buttons.length)%buttons.length;
        activate(nav,buttons[next].dataset.workspaceTab,true);
      });
    });
    activate(nav,nav.dataset.defaultTab||buttons[0]?.dataset.workspaceTab,false);
  });
  document.querySelectorAll("[data-open-workspace-tab]").forEach(function(button){
    button.addEventListener("click",function(){
      var group=button.dataset.workspaceGroup;
      var nav=document.querySelector('[data-workspace-tabs="'+group+'"]');
      if(nav)activate(nav,button.dataset.openWorkspaceTab,true);
    });
  });
})();
