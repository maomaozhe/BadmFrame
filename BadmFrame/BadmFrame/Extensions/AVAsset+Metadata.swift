import AVFoundation

extension AVAsset {
    var durationSec: Double {
        CMTimeGetSeconds(duration)
    }

    var naturalSize: CGSize {
        guard let track = tracks(withMediaType: .video).first else { return .zero }
        return track.naturalSize
    }

    var nominalFrameRate: Double {
        guard let track = tracks(withMediaType: .video).first else { return 0 }
        return Double(track.nominalFrameRate)
    }

    var videoCodec: String {
        guard let track = tracks(withMediaType: .video).first else { return "未知" }
        let descs = track.formatDescriptions as! [CMFormatDescription]
        guard let first = descs.first else { return "未知" }
        let codec = CMFormatDescriptionGetMediaSubType(first)
        return FourCharCode(codec).codecDisplayString
    }

    var isVariableFrameRate: Bool {
        guard let track = tracks(withMediaType: .video).first else { return false }
        return track.nominalFrameRate == 0
    }
}

extension FourCharCode {
    var codecDisplayString: String {
        switch self {
        case kCMVideoCodecType_H264: return "H.264"
        case kCMVideoCodecType_HEVC: return "HEVC"
        case kCMVideoCodecType_AppleProRes422: return "ProRes 422"
        case kCMVideoCodecType_AppleProRes4444: return "ProRes 4444"
        default: return "\(self)"
        }
    }
}
