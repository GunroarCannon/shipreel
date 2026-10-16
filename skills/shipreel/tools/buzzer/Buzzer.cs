// buzzer.exe - flash a red border around every screen + play a sound, then exit.
// Click-through, never steals focus. Build: powershell -File build.ps1 (uses the csc that ships with Windows).
//
//   buzzer.exe                      2s red flash + buzzer.mp3/wav next to the exe (or system sound)
//   buzzer.exe -t 5 -m "Need your input"   5 seconds, with a message banner
//   buzzer.exe -s none | beep | C:\path\sound.mp3     sound choice
//   buzzer.exe -c orange -w 16 -f 3        color, border width px, flashes per second
using System;
using System.Drawing;
using System.IO;
using System.Media;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

static class Native {
    [DllImport("winmm.dll", CharSet = CharSet.Unicode)]
    public static extern int mciSendString(string cmd, StringBuilder ret, int len, IntPtr hwnd);
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}

class BorderForm : Form {
    readonly int border; readonly Color color; readonly string message; public bool On = true;
    public BorderForm(Rectangle bounds, int border, Color color, string message) {
        this.border = border; this.color = color; this.message = message;
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true;
        StartPosition = FormStartPosition.Manual; Bounds = bounds;
        BackColor = Color.Magenta; TransparencyKey = Color.Magenta; DoubleBuffered = true;
    }
    protected override bool ShowWithoutActivation { get { return true; } }
    protected override CreateParams CreateParams {
        get {
            CreateParams cp = base.CreateParams;
            // WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
            cp.ExStyle |= 0x80000 | 0x20 | 0x80 | 0x08000000 | 0x8;
            return cp;
        }
    }
    protected override void OnPaint(PaintEventArgs e) {
        if (!On) return;
        Graphics g = e.Graphics; int w = ClientSize.Width, h = ClientSize.Height;
        using (SolidBrush b = new SolidBrush(color)) {
            g.FillRectangle(b, 0, 0, w, border); g.FillRectangle(b, 0, h - border, w, border);
            g.FillRectangle(b, 0, 0, border, h); g.FillRectangle(b, w - border, 0, border, h);
        }
        if (!string.IsNullOrEmpty(message)) {
            using (Font f = new Font("Segoe UI", 20, FontStyle.Bold)) {
                SizeF sz = g.MeasureString(message, f);
                float x = (w - sz.Width) / 2f, y = border + 18;
                using (SolidBrush bg = new SolidBrush(color)) g.FillRectangle(bg, x - 18, y - 8, sz.Width + 36, sz.Height + 16);
                g.DrawString(message, f, Brushes.White, x, y);
            }
        }
    }
}

static class Program {
    [STAThread]
    static int Main(string[] args) {
        double seconds = 2; string msg = null, sound = null, colorName = "red"; int width = 14; double hz = 4;
        for (int i = 0; i < args.Length; i++) {
            string a = args[i]; string v = i + 1 < args.Length ? args[i + 1] : null;
            if ((a == "-t" || a == "--time") && v != null) { seconds = double.Parse(v, System.Globalization.CultureInfo.InvariantCulture); i++; }
            else if ((a == "-m" || a == "--message") && v != null) { msg = v; i++; }
            else if ((a == "-s" || a == "--sound") && v != null) { sound = v; i++; }
            else if ((a == "-c" || a == "--color") && v != null) { colorName = v; i++; }
            else if ((a == "-w" || a == "--width") && v != null) { width = int.Parse(v); i++; }
            else if ((a == "-f" || a == "--flash") && v != null) { hz = double.Parse(v, System.Globalization.CultureInfo.InvariantCulture); i++; }
            else if (a == "-h" || a == "--help" || a == "/?") {
                Console.WriteLine("buzzer.exe [-t seconds=2] [-m message] [-s none|beep|file.mp3|file.wav] [-c red] [-w 14] [-f 4]");
                return 0;
            }
            else msg = msg == null ? a : msg + " " + a;  // loose words join the message (callers that don't quote)
        }
        try { Native.SetProcessDPIAware(); } catch { }
        Application.EnableVisualStyles();
        Color color = Color.FromName(colorName); if (!color.IsKnownColor) color = Color.Red;
        if (color.ToArgb() == Color.Magenta.ToArgb()) color = Color.FromArgb(255, 0, 254);

        // sound
        string exeDir = AppDomain.CurrentDomain.BaseDirectory;
        if (sound == null) {
            foreach (string n in new string[] { "buzzer.mp3", "buzzer.wav" })
                if (File.Exists(Path.Combine(exeDir, n))) { sound = Path.Combine(exeDir, n); break; }
            if (sound == null) sound = "beep";
        }
        bool mci = false;
        if (sound == "beep") SystemSounds.Exclamation.Play();
        else if (sound != "none" && File.Exists(sound)) {
            Native.mciSendString("open \"" + Path.GetFullPath(sound) + "\" type mpegvideo alias buzz", null, 0, IntPtr.Zero);
            mci = Native.mciSendString("play buzz", null, 0, IntPtr.Zero) == 0;
            if (!mci) SystemSounds.Exclamation.Play();
        }

        BorderForm[] forms = new BorderForm[Screen.AllScreens.Length];
        for (int i = 0; i < forms.Length; i++) {
            forms[i] = new BorderForm(Screen.AllScreens[i].Bounds, width, color, Screen.AllScreens[i].Primary ? msg : null);
            forms[i].Show();
        }
        Timer flash = new Timer(); flash.Interval = Math.Max(50, (int)(500 / Math.Max(0.1, hz)));
        flash.Tick += delegate { foreach (BorderForm f in forms) { f.On = !f.On; f.Invalidate(); } };
        if (hz > 0) flash.Start();
        Timer stop = new Timer(); stop.Interval = Math.Max(100, (int)(seconds * 1000));
        stop.Tick += delegate {
            stop.Stop(); flash.Stop();
            if (mci) Native.mciSendString("close buzz", null, 0, IntPtr.Zero);
            Application.Exit();
        };
        stop.Start();
        Application.Run();
        return 0;
    }
}
