// Apple Vision face finder for talking-head-shorts/track.py.
//   face <video>   prints a JSON array, one entry per frame: [centre x, centre y, face width] in the video's own
//                  pixels (origin top-left), or null when no face is found. The largest face wins.
import Foundation
import AVFoundation
import Vision

let args = CommandLine.arguments
if args.count < 2 { FileHandle.standardError.write("usage: face <video>\n".data(using: .utf8)!); exit(2) }
let asset = AVAsset(url: URL(fileURLWithPath: args[1]))
guard let track = asset.tracks(withMediaType: .video).first else { print("[]"); exit(0) }
let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(out); reader.startReading()
var rows: [String] = []
while let sb = out.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let req = VNDetectFaceRectanglesRequest()
    try? VNImageRequestHandler(cvPixelBuffer: pb, options: [:]).perform([req])
    let W = Double(CVPixelBufferGetWidth(pb)), H = Double(CVPixelBufferGetHeight(pb))
    if let f = (req.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }) {
        let b = f.boundingBox  // normalised, origin bottom-left
        rows.append("[\((b.midX*W*10).rounded()/10),\(((1-b.midY)*H*10).rounded()/10),\((b.width*W*10).rounded()/10)]")
    } else { rows.append("null") }
}
print("[" + rows.joined(separator: ",") + "]")
