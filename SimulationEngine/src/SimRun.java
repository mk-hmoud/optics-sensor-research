import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.function.Consumer;
import org.json.JSONArray;
import org.json.JSONObject;
import com.comsol.model.Model;
import com.comsol.model.util.*;

public class SimRun {

    // --- DATA STRUCTURES ---
	public record Configuration(
	        double n_ana, 
	        double initialEigenvalueSearch, 
	        double largeStep, 
	        double smallStep,
	        int maxIterations, 
	        String numberOfEigenValues, 
	        String modelPath,
	        String imagesDir, 
	        String resultsCsvPath
	    ) {}

	    public record ComplexNumber(double real, double imag) {
	        @Override public String toString() {
	            return String.format("%.6f + (%.6f)i", real, imag);
	        }
	    }

	    public record WavelengthResult(double wavelength, ComplexNumber neff, double loss) {}

	    public static void runSweep(Configuration config, Consumer<String> log, double startWl, double endWl, double stepWl) {
	        Model model = null;
	        try {
	            model = initializeAndLoadModel(config.modelPath, log);
	            if (model == null) return;
	            List<WavelengthResult> allResults = new ArrayList<>();

	            for (double wl = startWl; wl <= endWl; wl += stepWl) {
	                if (Thread.currentThread().isInterrupted()) {
	                    log.accept("--- Wavelength sweep cancelled by user ---");
	                    break;
	                }
	                log.accept(String.format("\n\n<<<<<<<< PROCESSING WAVELENGTH: %.1f nm >>>>>>>>\n", wl));
	                
	                ComplexNumber fundamentalMode = findFundamentalMode(model, config, wl, log);
	                
	                if (fundamentalMode != null) {
	                    double loss = calculateLoss(fundamentalMode);
	                    allResults.add(new WavelengthResult(wl, fundamentalMode, loss));
	                    log.accept(String.format("SUCCESS for %.1f nm. Loss: %.4f dB/cm", wl, loss));
	                } else {
	                    log.accept(String.format("FAILURE for %.1f nm. Could not find fundamental mode.", wl));
	                }
	            }
	            if (!Thread.currentThread().isInterrupted()) {
	                exportResultsToCSV(allResults, config.resultsCsvPath, log);
	            } 

	        } catch (Exception e) {
	            log.accept("A fatal error occurred: " + e.getMessage());
	            e.printStackTrace();
	        } finally {
	            if (model != null) {
	                log.accept("Disconnecting and shutting down engine.");
	                ModelUtil.disconnect();
	            }
	        }
	    }

    /**
     * The optimization loop that searches for the fundamental mode for a GIVEN WAVELENGTH.
     * @return The ComplexNumber of the fundamental mode, or null if not found.
     */
	    public static ComplexNumber findFundamentalMode(Model model, Configuration config, double wavelengthNm, Consumer<String> log) throws Exception {
	        model.param().set("w_length", wavelengthNm + "[nm]");
	        model.param().set("n_ana", String.valueOf(config.n_ana));
	        log.accept(String.format("Set model params: w_length=%.1f[nm], n_ana=%.4f", wavelengthNm, config.n_ana));

	        double currentEigenvalueSearch = config.initialEigenvalueSearch;
	        double currentStep = config.largeStep;
	        int previousDirection = 0;

	        for (int iteration = 1; iteration <= config.maxIterations; iteration++) {
	        	if (Thread.currentThread().isInterrupted()) {
	                log.accept("--- Optimization loop cancelled by user ---");
	                return null;
	            }
	            log.accept(String.format("\n--- Iteration #%d (Search: %.4f) ---", iteration, currentEigenvalueSearch));

	            runSimulationAndExport(model, currentEigenvalueSearch, config.numberOfEigenValues, config.imagesDir, log);
	            List<String> predictions = runPrediction(config, log);

	            int fundamentalCount = 0, higherCount = 0, lowerCount = 0, firstFundamentalIndex = -1;
	            for (int i = 0; i < predictions.size(); i++) {
	                String p = predictions.get(i);
	                if (p.equals("fundamental")) {
	                    fundamentalCount++;
	                    if (firstFundamentalIndex == -1) { firstFundamentalIndex = i; }
	                } else if (p.equals("higher")) {
	                    higherCount++;
	                } else if (p.equals("lower")) {
	                    lowerCount++;
	                }
	            }
	            
	            if (fundamentalCount == 2) {
	                log.accept("Found a pair of fundamental modes!");
	                String tempOutputFile = config.imagesDir + File.separator + "effectiveModeIndexes.txt";
	                return getEigenvalueFromFileByIndex(tempOutputFile, firstFundamentalIndex, log);
	            } 
	            
	            log.accept("\nINFO: Did not find a pair of fundamental modes. Analyzing results for next step.");
	            
	            int currentDirection = 0;
	            if (higherCount > lowerCount) currentDirection = -1;
	            else if (lowerCount > higherCount) currentDirection = 1;

	            if (currentDirection != 0 && (currentDirection == -previousDirection)) {
	                if (currentStep == config.largeStep) {
	                    log.accept("----> OVERSHOT TARGET! Switching from large steps to small steps.");
	                    currentStep = config.smallStep;
	                }
	            }
	            
	            if (currentDirection == 0) {
	                 log.accept("----> Ambiguous result. Keeping search value the same for next iteration.");
	            } else {
	                 log.accept(String.format("----> Adjusting search value. Old: %.4f, Step: %.4f, New: %.4f", 
	                                   currentEigenvalueSearch, (currentDirection * currentStep), (currentEigenvalueSearch + currentDirection * currentStep)));
	                 currentEigenvalueSearch += currentDirection * currentStep;
	            }
	            
	            if (currentDirection != 0) previousDirection = currentDirection;
	            if (iteration == config.maxIterations) log.accept("\nFAILURE: Reached max iterations without finding the fundamental mode pair.");
	        }
	        return null;
	    }

    /**
     * Calculates the propagation loss in dB/cm based on your formula.
     */
    public static double calculateLoss(ComplexNumber neff) {
        // loss = 8.686 * 2 * PI * Im(neff) * 10^6 / Re(neff)
        if (neff.real() == 0) return Double.NaN;
        return 8.686 * 2 * Math.PI * neff.imag() * 1e6 / neff.real();
    }

    /**
     * Writes the collected results to a CSV file.
     */
    public static void exportResultsToCSV(List<WavelengthResult> results, String filePath, Consumer<String> log) throws IOException {
        log.accept("\n--- Exporting final results to " + filePath + " ---");
        try (PrintWriter writer = new PrintWriter(new FileWriter(filePath))) {
            writer.println("Wavelength (nm),Re(neff),Im(neff),Loss (dB/cm)");
            for (WavelengthResult res : results) {
                writer.printf("%.2f,%.6f,%.6f,%.6f\n",
                    res.wavelength, res.neff.real(), res.neff.imag(), res.loss);
            }
        }
        log.accept("Export complete.");
    }
    
    /**
     * Initializes the COMSOL engine and loads the model file.
     */
    public static Model initializeAndLoadModel(String modelPath, Consumer<String> log) {
        try {
            log.accept("Starting COMSOL engine...");
            ModelUtil.initStandalone(false);
            log.accept("Engine launched.");
            log.accept("Loading model: " + modelPath);
            Model model = ModelUtil.load("MyModelTag", modelPath);
            log.accept("Model loaded successfully.");
            return model;
        } catch (IOException e) {
            log.accept("Failed to load model: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Sets parameters, runs the solver, and exports result images.
     */
    public static void runSimulationAndExport(Model model, double currentShift, String numEigs, String imagesDir, Consumer<String> log) {
        log.accept(String.format("Setting 'Search for eigenvalues around' to: %.4f", currentShift));
        model.sol("sol1").feature("e1").set("shift", String.valueOf(currentShift));
        model.sol("sol1").feature("e1").set("neigs", numEigs);
        
        log.accept("Running solver (sol1)...");
        model.sol("sol1").runAll();
        log.accept("Solver run complete.");
        
        log.accept("--- Exporting plots for all available modes ---");
        int plotsExported = 0;
        for (int i = 1; i < 1000; i++) {
            try {
                model.result("pg1").set("looplevel", i);
                String imageOutputPath = imagesDir + File.separator + String.format("mode_plot_%d.png", i);
                model.result().export("img1").set("filename", imageOutputPath);
                model.result().export("img1").run();
                plotsExported++;
            } catch (Exception e) {
                break; 
            }
        }
        log.accept("--- Exporting eigenvalue data to file ---");
        try {
            String tempOutputFile = imagesDir + File.separator + "effectiveModeIndexes.txt";
            model.result().export("data1").set("filename", tempOutputFile);
            model.result().export("data1").run();
            log.accept("Eigenvalue data exported successfully.");
        } catch (Exception e) {
            log.accept("ERROR: Failed to export eigenvalue data file. Check if the export node with tag 'data1' exists and is configured correctly.");
            e.printStackTrace();
        }
    }

    /**
     * HTTP request to the CNN MODEL server.
     */
    public static List<String> runPrediction(Configuration config, Consumer<String> log) throws java.io.IOException, InterruptedException {
        log.accept("\n--- Sending prediction request to Python server ---");
        
        HttpClient client = HttpClient.newHttpClient();
        String jsonBody = "{\"image_dir\": \"" + config.imagesDir.replace("\\", "\\\\") + "\"}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:5000/predict"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

        HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
        
        log.accept("Python Server Response (Status Code " + response.statusCode() + "):");
        String responseBody = response.body();

        JSONArray jsonArray = new JSONArray(responseBody);
        log.accept(jsonArray.toString(4));

        List<String> predictions = new ArrayList<>();
        for (int i = 0; i < jsonArray.length(); i++) {
            JSONObject obj = jsonArray.getJSONObject(i);
            if (obj.has("prediction")) {
                predictions.add(obj.getString("prediction"));
            }
        }
        
        log.accept("API request finished. Parsed " + predictions.size() + " predictions.");
        return predictions;
    }
    
    /**
     * Reads the exported data file to get the eigenvalue for a mode index.
     * @param filePath Path to the text file generated by COMSOL.
     * @param modeIndex The index of the mode to fetch.
     * @return ComplexNumber object for the mode.
     */
    public static ComplexNumber getEigenvalueFromFileByIndex(String filePath, int modeIndex, Consumer<String> log) throws java.io.IOException {
        File file = new File(filePath);
        try (java.util.Scanner scanner = new java.util.Scanner(file)) {
            while (scanner.hasNextLine()) {
                String line = scanner.nextLine();
                if (line.startsWith("%")) continue;

                String[] parts = line.trim().split("\\s+");
                int columnIndex = modeIndex + 2; // +2 to skip X and Y columns...
                
                if (parts.length > columnIndex) {
                    String complexStr = parts[columnIndex].replace("i", "");

                    int splitIndex = -1;

                    for (int j = complexStr.length() - 1; j > 0; j--) {
                        char c = complexStr.charAt(j);
                        if (c == '+' || c == '-') {
                            char charBefore = Character.toUpperCase(complexStr.charAt(j - 1));
                            if (charBefore != 'E') {
                                splitIndex = j;
                                break;
                            }
                        }
                    }
                    
                    if (splitIndex > 0) {
                        String realPartStr = complexStr.substring(0, splitIndex);
                        String imagPartStr = complexStr.substring(splitIndex);
                        
                        double realPart = Double.parseDouble(realPartStr);
                        double imagPart = Double.parseDouble(imagPartStr);
                        
                        return new ComplexNumber(realPart, imagPart);
                    } else {
                        return new ComplexNumber(Double.parseDouble(complexStr), 0.0);
                    }
                }
                break;
            }
        }
        throw new java.io.IOException("Could not find or parse eigenvalue data for mode index " + modeIndex);
    }
}