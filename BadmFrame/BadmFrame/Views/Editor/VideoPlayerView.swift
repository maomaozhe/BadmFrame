import SwiftUI
import AVKit

struct VideoPlayerView: View {
    @Bindable var viewModel: PlayerViewModel

    var body: some View {
        ZStack {
            if let player = viewModel.player {
                AVPlayerRepresentable(player: player)
                    .aspectRatio(16 / 9, contentMode: .fit)
            } else if viewModel.isLoading {
                VStack(spacing: 12) {
                    ProgressView()
                    Text("加载视频...")
                        .foregroundStyle(.secondary)
                }
            } else if let error = viewModel.errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(.red)
                    Text(error)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .background(Color.black)
        .onTapGesture {
            viewModel.togglePlayPause()
        }
        .overlay(alignment: .bottom) {
            playbackControls
                .padding(.horizontal)
                .padding(.bottom, 8)
                .background(.ultraThinMaterial)
        }
    }

    var playbackControls: some View {
        HStack(spacing: 12) {
            Button {
                viewModel.togglePlayPause()
            } label: {
                Image(systemName: viewModel.isPlaying ? "pause.fill" : "play.fill")
                    .font(.title2)
            }

            Text(viewModel.currentTime.preciseDisplayString)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.white)

            Spacer()

            Text(viewModel.duration.preciseDisplayString)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)

            if viewModel.duration > 0 {
                ProgressView(value: viewModel.currentTime, total: viewModel.duration)
                    .tint(.white)
                    .frame(width: 60)
            }
        }
    }
}

struct AVPlayerRepresentable: UIViewControllerRepresentable {
    let player: AVPlayer

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.showsPlaybackControls = false
        controller.videoGravity = .resizeAspect
        return controller
    }

    func updateUIViewController(_ controller: AVPlayerViewController, context: Context) {}
}
