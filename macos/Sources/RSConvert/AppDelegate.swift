import AppKit
import RSConvertCore
import ServiceManagement
import SwiftUI
import UniformTypeIdentifiers

@MainActor
final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate, NSWindowDelegate {
    let model = AppModel()
    private var statusItem: NSStatusItem!
    private var window: NSWindow?
    private var pendingOpen: [URL] = []
    private var finishedLaunching = false

    // MARK: Lifecycle

    func applicationWillFinishLaunching(_ notification: Notification) {
        NSApp.mainMenu = Self.makeMainMenu()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        let menu = NSMenu()
        menu.delegate = self
        statusItem.menu = menu
        // Accept drops onto the menu bar icon too.
        statusItem.button?.window?.registerForDraggedTypes([.fileURL])
        statusItem.button?.window?.delegate = self
        model.onStatusChange = { [weak self] in self?.updateStatusIcon() }
        updateStatusIcon()

        finishedLaunching = true
        let launchedAtLogin = NSAppleEventManager.shared().currentAppleEvent?
            .paramDescriptor(forKeyword: keyAEPropData)?.enumCodeValue == keyAELaunchedAsLogInItem
        if !launchedAtLogin || !pendingOpen.isEmpty { showWindow() } else { NSApp.setActivationPolicy(.accessory) }
        if !pendingOpen.isEmpty {
            model.enqueue(pendingOpen, origin: .manual)
            pendingOpen.removeAll()
        }
    }

    /// Files dropped on the Dock icon, opened with "Open With", or passed by `open -a`.
    func application(_ application: NSApplication, open urls: [URL]) {
        guard finishedLaunching else { pendingOpen += urls; return }
        showWindow()
        model.enqueue(urls, origin: .manual)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        showWindow()
        return true
    }

    // MARK: Window

    @objc func showWindow() {
        if window == nil {
            let window = NSWindow(
                contentRect: NSRect(x: 0, y: 0, width: 780, height: 680),
                styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            window.title = "RS Convert \(RSConvertVersion.string)"
            window.isReleasedWhenClosed = false
            window.contentView = DropHostingView(rootView: MainView(model: model), model: model)
            window.setFrameAutosaveName("MainWindow")
            if !window.setFrameUsingName("MainWindow") { window.center() }
            window.delegate = self
            self.window = window
        }
        // Show in the Dock and app switcher only while the window is open.
        NSApp.setActivationPolicy(.regular)
        window?.makeKeyAndOrderFront(nil)
        NSApp.activate()
    }

    func windowWillClose(_ notification: Notification) {
        guard (notification.object as? NSWindow) === window else { return }
        // Release the SwiftUI view hierarchy; the app lives on in the menu bar.
        window?.contentView = nil
        window = nil
        NSApp.setActivationPolicy(.accessory)
    }

    // MARK: Status item

    private func updateStatusIcon() {
        let symbol: String
        let tip: String
        if model.isBusy {
            symbol = "arrow.triangle.2.circlepath"
            tip = "Processing \(model.batchDone) of \(model.batchTotal)"
        } else if model.watchEnabled, let problem = model.watchProblem {
            symbol = "exclamationmark.triangle"
            tip = problem
        } else if model.watchEnabled, let folder = model.watchFolder {
            symbol = "guitars.fill"
            tip = "Watching \(folder.lastPathComponent)"
        } else {
            symbol = "guitars"
            tip = "RS Convert"
        }
        let image = NSImage(systemSymbolName: symbol, accessibilityDescription: tip)
        image?.isTemplate = true
        statusItem.button?.image = image
        statusItem.button?.toolTip = tip
    }

    func menuNeedsUpdate(_ menu: NSMenu) {
        menu.removeAllItems()
        let header: String
        if model.isBusy {
            header = "Processing \(model.batchDone) of \(model.batchTotal)…"
        } else if model.watchEnabled, let folder = model.watchFolder, model.watchProblem == nil {
            header = "Watching “\(folder.lastPathComponent)”"
        } else if let problem = model.watchEnabled ? model.watchProblem : nil {
            header = problem
        } else {
            header = "Idle"
        }
        let headerItem = NSMenuItem(title: header, action: nil, keyEquivalent: "")
        headerItem.isEnabled = false
        menu.addItem(headerItem)

        let recent = model.recentResults
        if !recent.isEmpty {
            menu.addItem(.separator())
            menu.addItem(NSMenuItem.sectionHeader(title: "Recent"))
            for entry in recent {
                let item = NSMenuItem(title: entry.message, action: #selector(revealLogEntry(_:)), keyEquivalent: "")
                item.target = self
                item.representedObject = entry.url
                item.image = NSImage(systemSymbolName: Self.symbol(for: entry.kind), accessibilityDescription: nil)
                item.toolTip = entry.message
                if entry.message.count > 60 { item.title = String(entry.message.prefix(57)) + "…" }
                menu.addItem(item)
            }
        }

        menu.addItem(.separator())
        menu.addItem(item("Open RS Convert", #selector(showWindow)))
        menu.addItem(item("Convert Files…", #selector(chooseFilesAction)))
        if model.outputFolder != nil { menu.addItem(item("Open Output Folder", #selector(openOutputFolder))) }

        menu.addItem(.separator())
        let watch = item(model.watchFolder.map { "Watch “\($0.lastPathComponent)”" } ?? "Watch a Folder…", #selector(toggleWatch))
        watch.state = model.watchEnabled ? .on : .off
        menu.addItem(watch)
        if model.watchFolder != nil {
            menu.addItem(item("Change Watch Folder…", #selector(chooseWatchFolder)))
            if model.watchEnabled { menu.addItem(item("Scan Now", #selector(scanNow))) }
        }

        menu.addItem(.separator())
        let login = item("Launch at Login", #selector(toggleLoginItem))
        login.state = SMAppService.mainApp.status == .enabled ? .on : .off
        menu.addItem(login)
        let version = NSMenuItem(title: "Version \(RSConvertVersion.string)", action: nil, keyEquivalent: "")
        version.isEnabled = false
        menu.addItem(version)
        menu.addItem(item("Quit RS Convert", #selector(NSApplication.terminate(_:)), key: "q", target: NSApp))
    }

    private func item(_ title: String, _ action: Selector, key: String = "", target: AnyObject? = nil) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = target ?? self
        return item
    }

    private static func symbol(for kind: LogEntry.Kind) -> String {
        switch kind {
        case .success: "checkmark.circle"
        case .skipped: "minus.circle"
        case .failure: "xmark.octagon"
        case .info: "info.circle"
        }
    }

    @objc private func revealLogEntry(_ sender: NSMenuItem) {
        if let url = sender.representedObject as? URL { NSWorkspace.shared.activateFileViewerSelecting([url]) }
    }

    @objc func chooseFilesAction() { Self.chooseFiles(model: model) }
    @objc private func openOutputFolder() { if let url = model.outputFolder { NSWorkspace.shared.open(url) } }
    @objc private func chooseWatchFolder() { model.chooseWatchFolder() }
    @objc private func scanNow() { model.rescanWatchFolder() }

    @objc private func toggleWatch() {
        if model.watchFolder == nil { model.chooseWatchFolder() } else { model.watchEnabled.toggle() }
    }

    @objc private func toggleLoginItem() {
        do {
            if SMAppService.mainApp.status == .enabled {
                try SMAppService.mainApp.unregister()
            } else {
                try SMAppService.mainApp.register()
            }
        } catch {
            model.info("Launch at Login could not be changed: \(error.localizedDescription)")
        }
    }

    static func chooseFiles(model: AppModel) {
        let panel = NSOpenPanel()
        panel.message = "Choose .psarc files or folders to process"
        panel.prompt = "Process"
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [UTType(filenameExtension: "psarc") ?? .data, .folder]
        NSApp.activate()
        if panel.runModal() == .OK { model.enqueue(panel.urls, origin: .manual) }
    }

    // MARK: Drops on the status item (its window forwards dragging calls to the delegate)

    @objc func draggingEntered(_ sender: any NSDraggingInfo) -> NSDragOperation {
        statusItem.button?.highlight(true)
        return .copy
    }

    @objc func draggingExited(_ sender: (any NSDraggingInfo)?) { statusItem.button?.highlight(false) }

    @objc func performDragOperation(_ sender: any NSDraggingInfo) -> Bool {
        statusItem.button?.highlight(false)
        let urls = DropReader.fileURLs(sender.draggingPasteboard)
        model.enqueue(urls, origin: .manual)
        return !urls.isEmpty
    }

    // MARK: Main menu (needed for standard shortcuts such as ⌘V in text fields)

    private static func makeMainMenu() -> NSMenu {
        let main = NSMenu()
        func submenu(_ title: String, _ items: [NSMenuItem]) {
            let menu = NSMenu(title: title)
            items.forEach(menu.addItem)
            let holder = NSMenuItem(title: title, action: nil, keyEquivalent: "")
            holder.submenu = menu
            main.addItem(holder)
        }
        func mi(_ title: String, _ action: Selector?, _ key: String, _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
            item.keyEquivalentModifierMask = mods
            return item
        }
        submenu("RS Convert", [
            mi("About RS Convert", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), ""),
            .separator(),
            mi("Hide RS Convert", #selector(NSApplication.hide(_:)), "h"),
            mi("Hide Others", #selector(NSApplication.hideOtherApplications(_:)), "h", [.command, .option]),
            .separator(),
            mi("Quit RS Convert", #selector(NSApplication.terminate(_:)), "q"),
        ])
        submenu("File", [
            mi("Convert Files…", #selector(AppDelegate.chooseFilesAction), "o"),
            mi("Close Window", #selector(NSWindow.performClose(_:)), "w"),
        ])
        submenu("Edit", [
            mi("Undo", Selector(("undo:")), "z"),
            mi("Redo", Selector(("redo:")), "z", [.command, .shift]),
            .separator(),
            mi("Cut", #selector(NSText.cut(_:)), "x"),
            mi("Copy", #selector(NSText.copy(_:)), "c"),
            mi("Paste", #selector(NSText.paste(_:)), "v"),
            mi("Select All", #selector(NSText.selectAll(_:)), "a"),
        ])
        submenu("Window", [
            mi("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"),
        ])
        return main
    }
}

/// Hosting view that makes the whole window a drop target for files and folders.
final class DropHostingView<Content: View>: NSHostingView<Content> {
    private weak var model: AppModel?

    init(rootView: Content, model: AppModel) {
        self.model = model
        super.init(rootView: rootView)
        registerForDraggedTypes([.fileURL])
    }

    required init(rootView: Content) { super.init(rootView: rootView) }
    @MainActor required dynamic init?(coder: NSCoder) { fatalError() }

    override func draggingEntered(_ sender: any NSDraggingInfo) -> NSDragOperation {
        model?.dropTargeted = true
        return .copy
    }

    override func draggingUpdated(_ sender: any NSDraggingInfo) -> NSDragOperation { .copy }

    override func draggingExited(_ sender: (any NSDraggingInfo)?) { model?.dropTargeted = false }

    override func performDragOperation(_ sender: any NSDraggingInfo) -> Bool {
        model?.dropTargeted = false
        let urls = DropReader.fileURLs(sender.draggingPasteboard)
        model?.enqueue(urls, origin: .manual)
        return !urls.isEmpty
    }
}
