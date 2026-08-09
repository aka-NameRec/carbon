#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, TrayIconEvent},
    Manager, RunEvent, WindowEvent,
};

const IDLE_ICON: &[u8] = include_bytes!("../icons/32x32.png");
const UNREAD_ICON: &[u8] = include_bytes!("../icons/unread/32x32.png");
const ERROR_ICON: &[u8] = include_bytes!("../icons/error/32x32.png");

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

#[tauri::command]
fn set_tray_state(app: tauri::AppHandle, state: String) -> Result<(), String> {
    let icon_bytes = match state.as_str() {
        "idle" => IDLE_ICON,
        "unread" => UNREAD_ICON,
        "error" => ERROR_ICON,
        _ => return Err(format!("unsupported tray state: {state}")),
    };
    let icon = Image::from_bytes(icon_bytes).map_err(|error| error.to_string())?;
    let tray = app
        .tray_by_id("carbon")
        .ok_or_else(|| "Carbon tray icon is unavailable".to_owned())?;
    tray.set_icon(Some(icon)).map_err(|error| error.to_string())
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            show_main_window(app);
        }))
        .invoke_handler(tauri::generate_handler![set_tray_state])
        .on_tray_icon_event(|app, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                ..
            } = event
            {
                show_main_window(app);
            }
        })
        .setup(|app| {
            let show = MenuItem::with_id(app, "show", "Show Carbon", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit Carbon", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;
            let _tray = tauri::tray::TrayIconBuilder::with_id("carbon")
                .menu(&menu)
                .tooltip("Carbon")
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "show" => show_main_window(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build Carbon desktop")
        .run(|app, event| {
            match event {
                RunEvent::WindowEvent {
                    label,
                    event: WindowEvent::CloseRequested { api, .. },
                    ..
                } if label == "main" => {
                    api.prevent_close();
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.hide();
                    }
                }
                RunEvent::ExitRequested { api, .. } => {
                    api.prevent_exit();
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.hide();
                    }
                }
                _ => {}
            }
        });
}
