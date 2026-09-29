using System;
using System.IO;
using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Runtime.InteropServices;
using System.Text.RegularExpressions;

public class PrintAgent
{
    const int Port = 8765;
    const string ZebraName = "ZDesigner GK420t";
    static TcpListener server;
    static string Root { get { return AppDomain.CurrentDomain.BaseDirectory; } }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public class DOCINFO { public string pDocName; public string pOutputFile; public string pDataType; }
    [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);
    [DllImport("winspool.drv", SetLastError = true)] static extern bool ClosePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool StartDocPrinter(IntPtr hPrinter, int level, [In] DOCINFO di);
    [DllImport("winspool.drv", SetLastError = true)] static extern bool EndDocPrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)] static extern bool StartPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)] static extern bool EndPagePrinter(IntPtr hPrinter);
    [DllImport("winspool.drv", SetLastError = true)]
    static extern bool WritePrinter(IntPtr hPrinter, byte[] pBytes, int dwCount, out int dwWritten);

    public static void Main()
    {
        try
        {
            server = new TcpListener(IPAddress.Loopback, Port);
            server.Start();
            Console.WriteLine("Emergency Blood Print Agent running on http://127.0.0.1:" + Port + "/");
            Console.WriteLine("Zebra target: " + ZebraName);
            while (true)
            {
                TcpClient c = server.AcceptTcpClient();
                ThreadPool.QueueUserWorkItem(HandleClient, c);
            }
        }
        catch (SocketException ex)
        {
            Console.WriteLine("Print Agent could not start: " + ex.Message);
            Console.WriteLine("Port " + Port + " may already be in use.");
            Console.ReadKey();
        }
        catch (Exception ex)
        {
            Console.WriteLine(ex.ToString());
            Console.ReadKey();
        }
    }

    static void HandleClient(object state)
    {
        TcpClient client = (TcpClient)state;
        try
        {
            NetworkStream ns = client.GetStream();
            string request = ReadRequest(ns);
            int split = request.IndexOf("\r\n\r\n", StringComparison.Ordinal);
            if (split < 0) { SendText(ns, 400, "Bad Request"); return; }
            string headers = request.Substring(0, split);
            string body = request.Substring(split + 4);
            string[] first = headers.Split(new string[] { "\r\n" }, StringSplitOptions.None);
            string[] reqLine = first[0].Split(' ');
            string method = reqLine.Length > 0 ? reqLine[0] : "";
            string path = reqLine.Length > 1 ? reqLine[1] : "/";
            int len = GetContentLength(headers);
            while (Encoding.UTF8.GetByteCount(body) < len)
            {
                byte[] buf = new byte[8192]; int n = ns.Read(buf, 0, buf.Length); if (n <= 0) break;
                body += Encoding.UTF8.GetString(buf, 0, n);
            }
            if (method == "OPTIONS") { SendResponse(ns, 204, "", "text/plain"); return; }
            if (method == "GET" && (path == "/" || path == "/index.html"))
            {
                string file = Path.Combine(Root, "index.html");
                if (!File.Exists(file)) { SendText(ns, 404, "index.html file not found."); return; }
                SendResponse(ns, 200, File.ReadAllText(file, Encoding.UTF8), "text/html; charset=utf-8"); return;
            }
            if (method == "GET" && path == "/status")
            {
                bool found = PrinterExists();
                string json = "{\"ok\":true,\"agent\":true,\"zebraFound\":" + (found ? "true" : "false") + ",\"printer\":\"" + ZebraName + "\"}";
                SendResponse(ns, 200, json, "application/json; charset=utf-8"); return;
            }
            if (method == "POST" && path == "/print/tag-bitmap")
            {
                PrintBitmap(body);
                SendResponse(ns, 200, "{\"ok\":true,\"message\":\"Compatibility Tag sent directly to Zebra GK420t\"}", "application/json; charset=utf-8"); return;
            }
            if (method == "POST" && path == "/print/tag-bitmaps")
            {
                PrintMultipleBitmaps(body);
                SendResponse(ns, 200, "{\"ok\":true,\"message\":\"Compatibility Tags sent in one print job\"}", "application/json; charset=utf-8"); return;
            }
            SendResponse(ns, 404, "{\"ok\":false,\"error\":\"Not found\"}", "application/json; charset=utf-8");
        }
        catch (Exception ex)
        {
            try { SendResponse(client.GetStream(), 500, "{\"ok\":false,\"error\":\"" + JsonEscape(ex.Message) + "\"}", "application/json; charset=utf-8"); } catch { }
        }
        finally { try { client.Close(); } catch { } }
    }

    static string ReadRequest(NetworkStream ns)
    {
        MemoryStream ms = new MemoryStream(); byte[] b = new byte[8192]; int n;
        while ((n = ns.Read(b, 0, b.Length)) > 0)
        {
            ms.Write(b, 0, n);
            string s = Encoding.UTF8.GetString(ms.ToArray());
            if (s.IndexOf("\r\n\r\n", StringComparison.Ordinal) >= 0) return s;
            if (ms.Length > 1024 * 1024) break;
        }
        return Encoding.UTF8.GetString(ms.ToArray());
    }
    static int GetContentLength(string h)
    {
        Match m = Regex.Match(h, "(?im)^Content-Length\\s*:\\s*(\\d+)");
        return m.Success ? Int32.Parse(m.Groups[1].Value) : 0;
    }
    static bool PrinterExists()
    {
        IntPtr h; bool ok = OpenPrinter(ZebraName, out h, IntPtr.Zero); if (ok) ClosePrinter(h); return ok;
    }
    static void EnsurePrinter()
    {
        if (!PrinterExists()) throw new Exception("Zebra printer '" + ZebraName + "' was not found in Windows.");
    }
    static void SendRaw(string zpl)
    {
        EnsurePrinter(); IntPtr h;
        if (!OpenPrinter(ZebraName, out h, IntPtr.Zero)) throw new Exception("Cannot open printer: " + ZebraName);
        try
        {
            DOCINFO di = new DOCINFO(); di.pDocName = "Emergency Blood Release Protocol - Compatibility Tag"; di.pDataType = "RAW";
            if (!StartDocPrinter(h, 1, di)) throw new Exception("StartDocPrinter failed");
            try
            {
                if (!StartPagePrinter(h)) throw new Exception("StartPagePrinter failed");
                try { byte[] data = Encoding.ASCII.GetBytes(zpl); int written; if (!WritePrinter(h, data, data.Length, out written)) throw new Exception("WritePrinter failed"); }
                finally { EndPagePrinter(h); }
            }
            finally { EndDocPrinter(h); }
        }
        finally { ClosePrinter(h); }
    }
    static void PrintBitmap(string json)
    {
        int w = JsonInt(json, "width"), h = JsonInt(json, "height"), rb = JsonInt(json, "rowBytes"); string hex = JsonString(json, "hex");
        if (w != 550 || h != 1041 || rb != 69) throw new Exception("Invalid tag bitmap size. Expected 550x1041.");
        if (String.IsNullOrEmpty(hex)) throw new Exception("Empty tag bitmap.");
        if (hex.Length != rb * h * 2) throw new Exception("Invalid bitmap data length.");
        SendRaw(BitmapZpl(hex, rb, h));
    }
    static void PrintMultipleBitmaps(string json)
    {
        MatchCollection ms = Regex.Matches(json, "\\\"width\\\"\\s*:\\s*550.*?\\\"hex\\\"\\s*:\\s*\\\"([0-9A-Fa-f]+)\\\"", RegexOptions.Singleline);
        if (ms.Count == 0) throw new Exception("No tag bitmaps supplied.");
        StringBuilder sb = new StringBuilder();
        for (int i=0;i<ms.Count;i++) sb.Append(BitmapZpl(ms[i].Groups[1].Value,69,1041));
        SendRaw(sb.ToString());
    }
    static string BitmapZpl(string hex, int rowBytes, int height)
    {
        int total = rowBytes * height;
        return "^XA\r\n^LRN\r\n^MD-2\r\n^PON\r\n^PW550\r\n^LL1041\r\n^FO0,0^GFA," + total + "," + total + "," + rowBytes + "," + hex + "^FS\r\n^XZ\r\n";
    }
    static int JsonInt(string j, string key)
    {
        Match m = Regex.Match(j, "\\\"" + Regex.Escape(key) + "\\\"\\s*:\\s*(\\d+)");
        if (!m.Success) throw new Exception("Missing field: " + key); return Int32.Parse(m.Groups[1].Value);
    }
    static string JsonString(string j, string key)
    {
        Match m = Regex.Match(j, "\\\"" + Regex.Escape(key) + "\\\"\\s*:\\s*\\\"([\\s\\S]*?)\\\"");
        return m.Success ? m.Groups[1].Value : "";
    }
    static string JsonEscape(string s) { return (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", " ").Replace("\n", " "); }
    static void SendText(NetworkStream ns, int status, string text) { SendResponse(ns,status,text,"text/plain; charset=utf-8"); }
    static void SendResponse(NetworkStream ns, int status, string body, string type)
    {
        byte[] data = Encoding.UTF8.GetBytes(body); string msg = status==200?"OK":status==204?"No Content":status==400?"Bad Request":status==404?"Not Found":"Internal Server Error";
        string h = "HTTP/1.1 " + status + " " + msg + "\r\nContent-Type: " + type + "\r\nContent-Length: " + data.Length + "\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Headers: Content-Type\r\nAccess-Control-Allow-Methods: GET,POST,OPTIONS\r\nConnection: close\r\n\r\n";
        byte[] head=Encoding.ASCII.GetBytes(h); ns.Write(head,0,head.Length); if(data.Length>0) ns.Write(data,0,data.Length); ns.Flush();
    }
}
