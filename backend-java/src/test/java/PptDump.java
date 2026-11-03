// Debug program: dumps first 3 slides of a PPTX to see actual text layout
import java.io.*;
import org.apache.poi.xslf.usermodel.*;
import org.apache.poi.openxml4j.util.ZipSecureFile;

public class PptDump {
    static { ZipSecureFile.setMinInflateRatio(0.001); }

    public static void main(String[] args) throws Exception {
        File dir = new File(args.length > 0 ? args[0] : "/app/demo");
        for (File f : dir.listFiles()) {
            if (!f.getName().endsWith(".pptx")) continue;
            System.out.println("FILE: " + f.getName());
            XMLSlideShow ppt = new XMLSlideShow(new FileInputStream(f));
            for (XSLFSlide slide : ppt.getSlides()) {
                StringBuilder sb = new StringBuilder();
                for (XSLFShape shape : slide.getShapes()) {
                    if (shape instanceof XSLFTextShape) {
                        String t = ((XSLFTextShape) shape).getText();
                        if (t != null && !t.trim().isEmpty()) sb.append(t.trim()).append("\n");
                    }
                    if (shape instanceof XSLFTable) {
                        XSLFTable table = (XSLFTable) shape;
                        for (XSLFTableRow row : table.getRows()) {
                            for (XSLFTableCell cell : row.getCells()) {
                                String t = cell.getText();
                                if (t != null && !t.trim().isEmpty()) sb.append(t.trim()).append(" | ");
                            }
                            sb.append("\n");
                        }
                    }
                }
                String text = sb.toString().trim();
                if (!text.isEmpty()) {
                    System.out.println("--- Slide " + slide.getSlideNumber() + " ---");
                    System.out.println(text.substring(0, Math.min(800, text.length())));
                    System.out.println();
                }
            }
            ppt.close();
            break; // only first file
        }
    }
}
