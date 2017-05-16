package GTX.TM.PMC;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.UnsupportedEncodingException;
import java.io.Writer;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ReadXML {

	public static String replaceBlank(String str) {
		String dest = "";
		if (str != null) {
			Pattern p = Pattern.compile("\t|\r|\n");
			Matcher m = p.matcher(str);
			dest = m.replaceAll("");
		}
		return dest;
	}

	public static Document readXMLFile(String filePath) {
		File f = new File(filePath);
		PMC2 pmc = new PMC2(f);
		Document d = pmc.next();
		return d;
	}

	public static void readXMLDir(String fileDir, String outputPath) {

		try {
			// String outputPath = "./data/output/result.txt";
			File root = new File(fileDir);
			File[] files = root.listFiles();
			for (File file : files) {
				String outputFileName = outputPath + file.getName() + ".txt";
				Document d = readXMLFile(file.getPath());
				System.out.println("Processing PMC: " + d.getID());
				String str = replaceBlank(d.getTitle()) + "\n" + replaceBlank(d.getAbs()) + "\n"
						+ replaceBlank(d.getBody()) + "\n";
				
				Writer out = new BufferedWriter(
						new OutputStreamWriter(new FileOutputStream(new File(outputFileName)), "UTF-8"));
				out.write(str);
				out.close();
			}

			System.out.println("FINISHED!");

		} catch (Exception e) {
			e.printStackTrace();
		}

	}

	public static void main(String[] args) {
		String fileDir = "./data/input";
		String outputDir = "./data/output/";
		readXMLDir(fileDir, outputDir);

	}

}
