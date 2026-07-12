import { createContext, useContext, useEffect, useMemo, useState } from "react";

export const languages = {
  en: { code: "en", label: "English", flagImage: "/assets/flags/uk.png", fallback: "🇬🇧", dir: "ltr" },
  fr: { code: "fr", label: "Français", flagImage: "/assets/flags/france.png", fallback: "🇫🇷", dir: "ltr" },
  fa: { code: "fa", label: "دری", flagImage: "/assets/flags/afghanistan.png", fallback: "🇦🇫", dir: "rtl" },
  ps: { code: "ps", label: "پښتو", flagImage: "/assets/flags/afghanistan.png", fallback: "🇦🇫", dir: "rtl" },
};

const en = {
  platformName:"Mission Operations Portal",
  platformShortName:"Operations Portal",
  platformSubtitle:"Internal operations, inventory, stock, approvals, communication, and reporting platform.",
  workspace:"Workspace", logistics:"Logistics", helpdesk:"Help Desk", knowledge:"Knowledge", tasks:"Tasks",
  admin:"Admin Center", inventory:"IMS", stock:"Stock", lanMessenger:"LAN Messenger",
  documents:"Documents", assets:"Assets", procurement:"Procurement", calendar:"Events",
  reports:"Reports", aiAssistant:"AI Assistant", login:"Login", logout:"Logout",
  sign:"Sign",
  dashboards:"Dashboards", myAssets:"My Assets",
  stockCards:"Stock Cards", stockMovements:"Movements", stockReports:"Stock Reports",
  allRequests:"All Requests", categories:"Categories", importData:"Import",
  dashboard:"Dashboard", search:"Search", notifications:"Notifications", profile:"Profile",
  settings:"Settings", createTicket:"Create ticket", myTickets:"My tickets", allTickets:"All tickets",
  open:"Open", close:"Close", save:"Save", cancel:"Cancel", submit:"Submit", exportCsv:"Export CSV",
  addItem:"Add item", requests:"Requests", status:"Status", quantity:"Quantity",
  category:"Category", description:"Description", organizationLogo:"Organization logo",
  organizationBranding:"Organization branding", signOut:"Sign out", about:"About",
  commandCenter:"Command center", smartQueue:"Ticket queue", knowledgeBase:"Knowledge base",
  userManagement:"User management", videoLibrary:"Help videos", workspaceSettings:"Categories & locations",
  newTicket:"New ticket", searchHelpdesk:"Search Help Desk…", searchMessages:"Search messages…", supportWorkspace:"IT support workspace",
  designedBy:"Public Demo Maintainers", serviceSupport:"Service support workspace",
  welcomeBack:"Welcome back", loginIntro:"Sign in to submit a request or continue an existing conversation.",
  email:"Work email", password:"Password", signIn:"Sign in", signingIn:"Signing in…",
  secureWorkspace:"Secure employee workspace", loginHero:"Support that keeps your work moving.",
  loginHeroText:"Report an issue, follow its progress, and speak directly with the person helping you—all in one place.",
  trackRequests:"Clear request tracking", directConversation:"Direct conversation with support",
  usefulGuides:"Useful guides for common issues", demoAccounts:"Demo accounts", chooseAccount:"Fill a demo account",
  privacyNote:"Your account and ticket information are protected.", yourRequests:"Your requests",
  myTicketsIntro:"See the latest status, assigned specialist, and conversation for every request.",
  noTickets:"No tickets yet", noTicketsText:"Create a support request when you need help.", all:"All",
  inProgress:"In progress", waiting:"Waiting for user", resolved:"Resolved", closed:"Closed",
  filterTickets:"Search your tickets…", owner:"Assigned to", created:"Created", request:"Request", priority:"Priority",
  newRequest:"New support request", helpQuestion:"What can we help with?",
  helpIntro:"Tell us what happened. We will route it to the right person and keep you updated.",
  accountDetails:"Added automatically from your account", routeRequest:"Route your request",
  routeHint:"Choose the closest category and your current work location.", location:"Location",
  selectLocation:"Select a location", none:"None", describeProblem:"Describe the problem",
  describeHint:"Error messages, timing, and the number of people affected are especially useful.",
  deviceTag:"Device Tag number", exampleTag:"For example, LT-2048", urgency:"How urgent is it?",
  shortTitle:"Short title", titleExample:"For example, VPN disconnects after sign-in",
  whatHappened:"What happened?", detailsPlaceholder:"When did it start? What do you see? What have you tried?",
  addFiles:"Add screenshots or files", filesHint:"Optional. Do not upload passwords or highly sensitive information.",
  dropFiles:"Drop files here, or choose from your device", fileRules:"PNG, JPG, WEBP, PDF, TXT or LOG · 5 MB each · maximum 5",
  secureFiles:"Secure, authenticated file storage.", submitRequest:"Submit request", creatingRequest:"Creating request…",
  peopleAccess:"People and access", userManagementIntro:"Add employees individually or import accounts from a CSV file.",
  csvTemplate:"CSV template", importCsv:"Import CSV", addUser:"Add user", totalPeople:"Total people",
  activeAccounts:"Active accounts", administrators:"Administrators", supportAgents:"Support agents",
  employeeDirectory:"Employee directory", settingsTitle:"Categories and locations",
  settingsIntro:"These options appear directly on the employee ticket form.", ticketCategories:"Ticket categories",
  supportLocations:"Support locations", add:"Add", active:"Active", hidden:"Hidden",
  selfService:"Self-service learning", quickHelpVideos:"Quick help videos",
  videosIntro:"Short, approved instructions for issues employees can solve safely.", addVideo:"Add video",
  noVideos:"No videos here yet", knowledgeIntro:"Trusted internal solutions for recurring support issues.",
  newArticle:"New article", approvedSolution:"Approved solution", title:"Title", publish:"Publish",
  serviceOverview:"Service desk overview", todaysSupport:"Today’s support picture", systemsOperational:"Systems operational",
  openQueue:"Open ticket queue", activeWorkload:"Active workload", highRisk:"High-risk queue",
  awaitingApproval:"Awaiting approval", resolutionRate:"Resolution rate", loading:"Loading…",
  comingSoon:"Coming Soon", accessGranted:"Access granted", openModule:"Open", backWorkspace:"Back to Workspace",
  items:"Items", myRequests:"My requests", manageRequests:"Manage requests", addStockItem:"Add stock item",
  requestItem:"Request item", available:"Available", lowStock:"Low Stock", outOfStock:"Out of Stock",
  organizationSettings:"Organization Settings", poweredBy:"Operations Portal",
  changePicture:"Change picture", removePicture:"Remove picture", uploadPicture:"Upload picture",
};

const fr = {
  workspace:"Espace de travail",helpdesk:"Assistance",knowledge:"Connaissances",tasks:"Tâches",admin:"Centre d’administration",
  inventory:"SGI",stock:"Stock",lanMessenger:"Messagerie LAN",documents:"Documents",assets:"Actifs",
  dashboards:"Tableaux de bord",myAssets:"Mes actifs",stockCards:"Fiches de stock",stockMovements:"Mouvements",stockReports:"Rapports de stock",allRequests:"Toutes les demandes",categories:"Catégories",importData:"Importer",
  procurement:"Achats",calendar:"Événements",reports:"Rapports",aiAssistant:"Assistant IA",login:"Connexion",
  logout:"Déconnexion",dashboard:"Tableau de bord",search:"Rechercher",notifications:"Notifications",profile:"Profil",
  settings:"Paramètres",createTicket:"Créer un ticket",myTickets:"Mes tickets",allTickets:"Tous les tickets",
  open:"Ouvrir",close:"Fermer",save:"Enregistrer",cancel:"Annuler",submit:"Envoyer",exportCsv:"Exporter CSV",
  addItem:"Ajouter un article",requests:"Demandes",status:"Statut",quantity:"Quantité",category:"Catégorie",
  description:"Description",organizationLogo:"Logo de l’organisation",organizationBranding:"Identité de l’organisation",
  signOut:"Se déconnecter",about:"À propos",welcomeBack:"Bon retour",email:"E-mail professionnel",
  password:"Mot de passe",signIn:"Se connecter",signingIn:"Connexion…",myTicketsIntro:"Suivez le statut et les échanges de chaque demande.",
  noTickets:"Aucun ticket",all:"Tous",inProgress:"En cours",waiting:"En attente de l’utilisateur",resolved:"Résolu",
  closed:"Fermé",owner:"Assigné à",created:"Créé",priority:"Priorité",location:"Lieu",none:"Aucun",
  urgency:"Urgence",title:"Titre",add:"Ajouter",active:"Actif",hidden:"Masqué",loading:"Chargement…",
  comingSoon:"Bientôt disponible",accessGranted:"Accès autorisé",openModule:"Ouvrir",backWorkspace:"Retour à l’espace",
  items:"Articles",myRequests:"Mes demandes",manageRequests:"Gérer les demandes",requestItem:"Demander",
  available:"Disponible",lowStock:"Stock faible",outOfStock:"Rupture de stock",poweredBy:"Operations Portal",
  addStockItem:"Ajouter au stock",changePicture:"Changer la photo",removePicture:"Supprimer la photo",uploadPicture:"Téléverser la photo",
};
const fa = {
  workspace:"فضای کاری",helpdesk:"میز کمک",knowledge:"دانش",tasks:"وظایف",admin:"مرکز مدیریت",inventory:"مدیریت موجودی",
  stock:"درخواست اجناس",lanMessenger:"پیام‌رسان داخلی",documents:"اسناد",assets:"دارایی‌ها",procurement:"تدارکات",
  calendar:"تقویم",reports:"گزارش‌ها",aiAssistant:"دستیار هوش مصنوعی",login:"ورود",logout:"خروج",
  dashboards:"داشبوردها",myAssets:"دارایی‌های من",stockCards:"کارت‌های موجودی",stockMovements:"حرکات",stockReports:"گزارش‌های موجودی",allRequests:"همه درخواست‌ها",categories:"دسته‌بندی‌ها",importData:"وارد کردن",
  dashboard:"داشبورد",search:"جستجو",notifications:"اعلان‌ها",profile:"پروفایل",settings:"تنظیمات",
  createTicket:"ایجاد تکت",myTickets:"تکت‌های من",allTickets:"همه تکت‌ها",open:"باز",close:"بستن",
  save:"ذخیره",cancel:"لغو",submit:"ارسال",exportCsv:"صدور CSV",addItem:"افزودن قلم",requests:"درخواست‌ها",
  status:"وضعیت",quantity:"تعداد",category:"دسته‌بندی",description:"توضیحات",organizationLogo:"لوگوی سازمان",
  organizationBranding:"نشان و هویت سازمان",signOut:"خروج",about:"درباره",welcomeBack:"خوش آمدید",
  email:"ایمیل کاری",password:"رمز عبور",signIn:"ورود",signingIn:"در حال ورود…",all:"همه",
  inProgress:"در حال اجرا",waiting:"منتظر کاربر",resolved:"حل‌شده",closed:"بسته",owner:"مسئول",
  created:"ایجاد شده",priority:"اولویت",location:"موقعیت",none:"هیچ",urgency:"فوریت",title:"عنوان",
  add:"افزودن",active:"فعال",hidden:"پنهان",loading:"در حال بارگذاری…",comingSoon:"به‌زودی",
  accessGranted:"دسترسی مجاز",openModule:"باز کردن",backWorkspace:"بازگشت به فضای کاری",
  items:"اقلام",myRequests:"درخواست‌های من",manageRequests:"مدیریت درخواست‌ها",requestItem:"درخواست",
  available:"موجود",lowStock:"موجودی کم",outOfStock:"ناموجود",poweredBy:"Operations Portal",
  addStockItem:"افزودن جنس",changePicture:"تغییر عکس",removePicture:"حذف عکس",uploadPicture:"بارگذاری عکس",
};
const ps = {
  workspace:"کاري چاپېریال",helpdesk:"مرستندویه مرکز",knowledge:"پوهه",tasks:"دندې",admin:"اداري مرکز",
  inventory:"د موجودۍ مدیریت",stock:"د توکو غوښتنه",lanMessenger:"داخلي پیغامونه",documents:"اسناد",
  assets:"شتمنۍ",procurement:"تدارکات",calendar:"کلیزه",reports:"راپورونه",aiAssistant:"د مصنوعي ځیرکتیا مرستیال",
  dashboards:"ډشبورډونه",myAssets:"زما شتمنۍ",stockCards:"د توکو کارتونه",stockMovements:"حرکتونه",stockReports:"د توکو راپورونه",allRequests:"ټولې غوښتنې",categories:"کټګورۍ",importData:"واردول",
  login:"ننوتل",logout:"وتل",dashboard:"ډشبورډ",search:"لټون",notifications:"خبرتیاوې",profile:"پروفایل",
  settings:"تنظیمات",createTicket:"ټکټ جوړول",myTickets:"زما ټکټونه",allTickets:"ټول ټکټونه",
  open:"خلاص",close:"تړل",save:"خوندي کول",cancel:"لغوه",submit:"لېږل",exportCsv:"CSV صادرول",
  addItem:"توکی زیاتول",requests:"غوښتنې",status:"حالت",quantity:"شمېر",category:"کټګوري",
  description:"تشریح",organizationLogo:"د ادارې نښان",organizationBranding:"د ادارې بڼه",
  signOut:"وتل",about:"په اړه",welcomeBack:"ښه راغلاست",email:"کاري برېښنالیک",password:"پټنوم",
  signIn:"ننوتل",signingIn:"ننوتل روان دي…",all:"ټول",inProgress:"د کار لاندې",waiting:"د کارن په تمه",
  resolved:"حل شوی",closed:"تړل شوی",owner:"مسئول",created:"جوړ شوی",priority:"لومړیتوب",
  location:"ځای",none:"هیڅ",urgency:"بیړنیوالی",title:"سرلیک",add:"زیاتول",active:"فعال",
  hidden:"پټ",loading:"بارېږي…",comingSoon:"ژر راځي",accessGranted:"لاسرسی ورکړل شوی",
  openModule:"پرانیستل",backWorkspace:"کاري چاپېریال ته ستنېدل",items:"توکي",myRequests:"زما غوښتنې",
  manageRequests:"غوښتنې اداره کول",requestItem:"غوښتنه",available:"موجود",lowStock:"کم موجودي",
  outOfStock:"خلاص شوی",poweredBy:"Operations Portal",
  addStockItem:"توکی زیاتول",changePicture:"انځور بدلول",removePicture:"انځور لرې کول",uploadPicture:"انځور پورته کول",
};

Object.assign(fr, {
  logistics:"Logistique", inventory:"SGI", sign:"Signature numérique",
  searchMessages:"Rechercher dans les messages…",
});
Object.assign(fa, {
  workspace:"فضای کاری", logistics:"لوژستیک", helpdesk:"میز کمک",
  knowledge:"دانشنامه", tasks:"وظایف", admin:"مرکز مدیریت",
  inventory:"آی ام اس", stock:"ذخیره", lanMessenger:"پیام‌رسان داخلی",
  documents:"اسناد", assets:"دارایی‌ها", procurement:"تدارکات",
  calendar:"تقویم", reports:"گزارش‌ها", dashboards:"داشبوردها",
  sign:"امضا", search:"جستجو", searchMessages:"جستجوی پیام‌ها…",
  signOut:"خروج", about:"درباره",
});
Object.assign(ps, {
  workspace:"کاري چاپېریال", logistics:"لوژستیک", helpdesk:"د مرستې مرکز",
  knowledge:"پوهه", tasks:"دندې", admin:"د ادارې مرکز",
  inventory:"آی ام اس", stock:"زېرمه", lanMessenger:"داخلي پیغام رسوونکی",
  documents:"اسناد", assets:"شتمنۍ", procurement:"تدارکات",
  calendar:"کلیزه", reports:"راپورونه", dashboards:"ډشبورډونه",
  sign:"لاسلیک", search:"لټون", searchMessages:"د پیغامونو لټون…",
  signOut:"وتل", about:"په اړه",
});

const translations = { en, fr:{...en,...fr}, fa:{...en,...fa}, ps:{...en,...ps} };
const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem("faza-language") || localStorage.getItem("language");
    return languages[saved] ? saved : "en";
  });
  const value = useMemo(() => ({
    language, setLanguage, languages, direction: languages[language].dir,
    t: (key) => translations[language]?.[key] || en[key] || key,
  }), [language]);
  useEffect(() => {
    localStorage.setItem("faza-language", language);
    document.documentElement.lang = language;
    document.documentElement.dir = "ltr";
    document.documentElement.dataset.textDirection = languages[language].dir;
  }, [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
export const useTranslation = () => useContext(LanguageContext);

