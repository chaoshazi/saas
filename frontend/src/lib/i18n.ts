import i18n from "i18next";
import { initReactI18next } from "react-i18next";

i18n.use(initReactI18next).init({
  resources: {
    zh: {
      translation: {
        login: "登录",
        register: "注册",
        email: "邮箱",
        password: "密码",
        fullName: "姓名",
        logout: "退出登录",
        dashboard: "工作台",
        projects: "项目",
        teams: "团队",
        documents: "文档",
        notifications: "通知",
        settings: "设置",
        billing: "计费",
        adminUsers: "用户管理",
        adminAudit: "审计日志",
        create: "创建",
        name: "名称",
        description: "描述",
      },
    },
    en: {
      translation: {
        login: "Sign in",
        register: "Sign up",
        email: "Email",
        password: "Password",
        fullName: "Full name",
        logout: "Log out",
        dashboard: "Dashboard",
        projects: "Projects",
        teams: "Teams",
        documents: "Documents",
        notifications: "Notifications",
        settings: "Settings",
        billing: "Billing",
        adminUsers: "Users",
        adminAudit: "Audit log",
        create: "Create",
        name: "Name",
        description: "Description",
      },
    },
  },
  lng: localStorage.getItem("locale") || "zh",
  fallbackLng: "zh",
  interpolation: { escapeValue: false },
});

export default i18n;
