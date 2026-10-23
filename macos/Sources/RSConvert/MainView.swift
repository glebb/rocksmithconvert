import AppKit
import RSConvertCore
import SwiftUI

struct MainView: View {
    @Bindable var model: AppModel

    var body: some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 0) {
                SettingsForm(model: model)
                    .frame(width: 340)
                DropZone(model: model)
                    .padding(16)
            }
            .frame(minHeight: 470)
            .layoutPriority(1)
            Divider()
            LogView(model: model)
                .frame(minHeight: 110, idealHeight: 160, maxHeight: 240)
        }
        .frame(minWidth: 720, minHeight: 600)
    }
}

private struct SettingsForm: View {
    @Bindable var model: AppModel

    var body: some View {
        Form {
            Section("Conversion") {
                Picker("Convert to", selection: $model.targetPlatform) {
                    Text("Don't convert").tag(Platform?.none)
                    ForEach(Platform.allCases, id: \.self) { Text($0.displayName).tag(Platform?.some($0)) }
                }
                Picker("Rename", selection: $model.renameScheme) {
                    Text("Keep name").tag(RenameScheme?.none)
                    ForEach(RenameScheme.allCases, id: \.self) { Text($0.displayName).tag(RenameScheme?.some($0)) }
                }
                .help("Short: Artist (10) – Song, about 20 letters. Full: Artist – Song. Avoids issues with long CDLC names.")
                Toggle("Change App ID", isOn: $model.appIDEnabled)
                if model.appIDEnabled {
                    TextField("App ID", text: $model.appID, prompt: Text("221680"))
                        .monospacedDigit()
                        .foregroundStyle(ConvertOptions.isValidAppID(model.appID) ? Color.primary : Color.red)
                }
                Toggle("Overwrite existing files", isOn: $model.overwrite)
            }
            Section("Output folder") {
                FolderRow(url: model.outputFolder, placeholder: "Not chosen", action: model.chooseOutputFolder)
            }
            Section {
                Toggle("Watch folder in background", isOn: $model.watchEnabled)
                FolderRow(url: model.watchFolder, placeholder: "Not chosen", action: model.chooseWatchFolder)
                if let problem = model.watchProblem, model.watchEnabled {
                    Label(problem, systemImage: "exclamationmark.triangle.fill").foregroundStyle(.orange).font(.callout)
                }
                Toggle("Notify when files are converted", isOn: $model.notifyOnBackground)
                    .onChange(of: model.notifyOnBackground) { _, on in if on { Notifier.requestAuthorization() } }
            } header: {
                Text("Watch folder")
            } footer: {
                Text("New .psarc files appearing here are processed automatically, even with this window closed.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
    }
}

private struct FolderRow: View {
    let url: URL?
    let placeholder: String
    let action: () -> Void

    var body: some View {
        HStack {
            if let url {
                Image(nsImage: NSWorkspace.shared.icon(forFile: url.path)).resizable().frame(width: 16, height: 16)
                Text(url.lastPathComponent).lineLimit(1).truncationMode(.middle).help(url.path)
            } else {
                Text(placeholder).foregroundStyle(.secondary)
            }
            Spacer()
            if let url {
                Button { NSWorkspace.shared.open(url) } label: { Image(systemName: "arrow.up.forward.square") }
                    .buttonStyle(.borderless).help("Open in Finder")
            }
            Button("Choose…", action: action)
        }
    }
}

private struct DropZone: View {
    let model: AppModel
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 14)
                .strokeBorder(style: StrokeStyle(lineWidth: 2, dash: [8, 6]))
                .foregroundStyle(model.dropTargeted ? Color.accentColor : Color.secondary.opacity(0.5))
                .background(RoundedRectangle(cornerRadius: 14).fill(model.dropTargeted ? Color.accentColor.opacity(0.08) : Color.clear))
            VStack(spacing: 12) {
                if model.isBusy {
                    ProgressView(value: model.progress)
                        .frame(maxWidth: 220)
                    Text("Processing \(model.batchDone) of \(model.batchTotal)…").foregroundStyle(.secondary)
                } else {
                    Image(systemName: "square.and.arrow.down.on.square")
                        .font(.system(size: 44, weight: .light))
                        .foregroundStyle(model.dropTargeted ? Color.accentColor : Color.secondary)
                    Text("Drop .psarc files or folders").font(.title3)
                    if let problem = model.configurationProblem {
                        Text(problem).font(.callout).foregroundStyle(.orange)
                    } else {
                        Text(summary).font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }
                    Button("Choose Files…") { AppDelegate.chooseFiles(model: model) }
                }
            }
            .padding()
        }
    }

    private var summary: String {
        var parts = [String]()
        if let p = model.targetPlatform { parts.append("convert to \(p.displayName)") }
        if let r = model.renameScheme { parts.append("\(r.displayName.lowercased()) rename") }
        if model.appIDEnabled { parts.append("App ID \(model.appID)") }
        return "Will " + parts.joined(separator: ", ") + ".\nOriginals are never modified."
    }
}

private struct LogView: View {
    let model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack {
                Text("Activity").font(.headline)
                Spacer()
                Button("Clear", action: model.clearLog).disabled(model.log.isEmpty)
            }
            .padding(.horizontal, 12).padding(.vertical, 6)
            ScrollViewReader { proxy in
                List(model.log) { entry in
                    LogRow(entry: entry).id(entry.id)
                }
                .listStyle(.plain)
                .onChange(of: model.log.last?.id) { _, id in
                    if let id { proxy.scrollTo(id, anchor: .bottom) }
                }
            }
        }
    }
}

private struct LogRow: View {
    let entry: LogEntry

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            icon
            Text(entry.message).textSelection(.enabled).lineLimit(3)
            Spacer()
            Text(entry.date, style: .time).font(.caption).foregroundStyle(.secondary).monospacedDigit()
        }
        .contextMenu {
            if let url = entry.url {
                Button("Show in Finder") { NSWorkspace.shared.activateFileViewerSelecting([url]) }
            }
            Button("Copy") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(entry.message, forType: .string)
            }
        }
    }

    @ViewBuilder private var icon: some View {
        switch entry.kind {
        case .success: Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
        case .skipped: Image(systemName: "minus.circle.fill").foregroundStyle(.secondary)
        case .failure: Image(systemName: "xmark.octagon.fill").foregroundStyle(.red)
        case .info: Image(systemName: "info.circle").foregroundStyle(.secondary)
        }
    }
}

enum DropReader {
    static func fileURLs(_ pasteboard: NSPasteboard) -> [URL] {
        pasteboard.readObjects(forClasses: [NSURL.self], options: [.urlReadingFileURLsOnly: true]) as? [URL] ?? []
    }
}
