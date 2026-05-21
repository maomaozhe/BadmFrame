import Foundation
import AVFoundation

@Observable
final class PlayerViewModel {
    var player: AVPlayer?
    var currentTime: Double = 0
    var duration: Double = 0
    var isPlaying: Bool = false
    var isLoading: Bool = false
    var errorMessage: String?

    private var timeObserver: Any?

    func loadVideo(url: URL) {
        cleanup()
        isLoading = true
        errorMessage = nil

        let asset = AVAsset(url: url)
        let playerItem = AVPlayerItem(asset: asset)
        let newPlayer = AVPlayer(playerItem: playerItem)
        self.player = newPlayer

        Task {
            do {
                let dur = try await asset.load(.duration)
                duration = CMTimeGetSeconds(dur)
                isLoading = false
            } catch {
                errorMessage = "无法加载视频: \(error.localizedDescription)"
                isLoading = false
            }
        }

        timeObserver = newPlayer.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.05, preferredTimescale: 600), queue: .main) { [weak self] _ in
            self?.currentTime = CMTimeGetSeconds(newPlayer.currentTime())
        }

        NotificationCenter.default.addObserver(forName: .AVPlayerItemDidPlayToEndTime, object: playerItem, queue: .main) { [weak self] _ in
            self?.isPlaying = false
        }
    }

    func togglePlayPause() {
        guard let player else { return }
        if isPlaying {
            player.pause()
        } else {
            player.play()
        }
        isPlaying.toggle()
    }

    func seek(to seconds: Double) {
        let time = CMTime(seconds: seconds, preferredTimescale: 600)
        player?.seek(to: time, toleranceBefore: .zero, toleranceAfter: .zero)
        currentTime = seconds
    }

    func cleanup() {
        if let observer = timeObserver {
            player?.removeTimeObserver(observer)
        }
        player?.pause()
        player = nil
        isPlaying = false
        currentTime = 0
        duration = 0
        isLoading = false
        errorMessage = nil
    }
}
