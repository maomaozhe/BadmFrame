import SwiftUI

struct EmptyStateView: View {
    let icon: String
    let title: String
    let subtitle: String
    var action: (() -> Void)?
    var actionLabel: String?

    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 40))
                .foregroundStyle(.secondary)

            Text(title)
                .font(.headline)

            Text(subtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            if let action, let actionLabel {
                Button(action: action) {
                    Text(actionLabel)
                }
                .buttonStyle(.bordered)
                .padding(.top, 8)
            }
        }
        .padding()
    }
}
