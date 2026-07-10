export const themes=[
  {id:"operations-blue",name:"Operations Blue",primary:"#2563eb",sidebar:"#111b31",topbar:"#ffffff",active:"#1d2b48",accent:"#eaf2ff",background:"#f4f6fa"},
  {id:"emerald-green",name:"Emerald Green",primary:"#0f9f72",sidebar:"#102c28",topbar:"#ffffff",active:"#19453d",accent:"#e4f7f0",background:"#f3f8f6"},
  {id:"royal-purple",name:"Royal Purple",primary:"#7357c7",sidebar:"#211a3d",topbar:"#ffffff",active:"#36295d",accent:"#f0ecff",background:"#f6f4fa"},
  {id:"slate-dark",name:"Slate Dark",primary:"#4f7cac",sidebar:"#111827",topbar:"#1f2937",active:"#334155",accent:"#e7edf4",background:"#eef1f5"},
  {id:"sky-light",name:"Sky Light",primary:"#1489c9",sidebar:"#17324a",topbar:"#f8fcff",active:"#224b69",accent:"#e3f5ff",background:"#f2f9fc"},
  {id:"amber-warm",name:"Amber Warm",primary:"#c47a12",sidebar:"#352615",topbar:"#fffdf8",active:"#59401d",accent:"#fff2d9",background:"#faf7f1"},
  {id:"rose-soft",name:"Rose Soft",primary:"#c34f72",sidebar:"#3a1e2b",topbar:"#fffafb",active:"#5c2d42",accent:"#ffe9f0",background:"#faf5f7"},
  {id:"teal-professional",name:"Teal Professional",primary:"#0c8b87",sidebar:"#123334",topbar:"#ffffff",active:"#1c5050",accent:"#e2f6f4",background:"#f2f8f8"},
  {id:"indigo-modern",name:"Indigo Modern",primary:"#4f5ed7",sidebar:"#171d3b",topbar:"#ffffff",active:"#293261",accent:"#e9ebff",background:"#f4f5fa"},
  {id:"neutral-gray",name:"Neutral Gray",primary:"#5f6b7a",sidebar:"#222831",topbar:"#ffffff",active:"#343d49",accent:"#eceff2",background:"#f5f6f7"},
];
export const themeById=id=>themes.find(theme=>theme.id===id)||themes[0];

