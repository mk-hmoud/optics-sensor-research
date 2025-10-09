import javax.swing.*;
import java.awt.*;
import java.io.File;
import java.io.OutputStream;
import java.io.PrintStream;
import java.util.function.Consumer;

public class SimGUI extends JFrame {

    private final JTextField nAnaField, startWlField, endWlField, stepWlField, initialSearchField;
    private final JButton startButton;
    private final JButton cancelButton;
    private final JTextArea logArea;
    private SwingWorker<Void, String> worker;

    public SimGUI() {
        setTitle("COMSOL Simulation Runner");
        setSize(800, 600);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);

        // --- Input Panel ---
        JPanel inputPanel = new JPanel(new GridBagLayout());
        inputPanel.setBorder(BorderFactory.createTitledBorder("Simulation Parameters"));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.anchor = GridBagConstraints.WEST;

        nAnaField = addField(inputPanel, gbc, "Analyte Refractive Index (n_ana):", 0, "1.33");
        startWlField = addField(inputPanel, gbc, "Start Wavelength (nm):", 1, "800");
        endWlField = addField(inputPanel, gbc, "End Wavelength (nm):", 2, "900");
        stepWlField = addField(inputPanel, gbc, "Wavelength Step (nm):", 3, "10");
        initialSearchField = addField(inputPanel, gbc, "Initial Eigenvalue Search:", 4, "1.44");

        // --- Control Panel ---
        startButton = new JButton("Start Wavelength Sweep");
        cancelButton = new JButton("Cancel Run");
        cancelButton.setEnabled(false);
        JPanel controlPanel = new JPanel(new FlowLayout(FlowLayout.CENTER));
        controlPanel.add(startButton);
        controlPanel.add(cancelButton);

        // --- Log Panel ---
        logArea = new JTextArea();
        logArea.setEditable(false);
        logArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane logScrollPane = new JScrollPane(logArea);
        logScrollPane.setBorder(BorderFactory.createTitledBorder("Log Output"));

        // --- Layout ---
        Container contentPane = getContentPane();
        contentPane.setLayout(new BorderLayout());
        contentPane.add(inputPanel, BorderLayout.NORTH);
        contentPane.add(logScrollPane, BorderLayout.CENTER);
        contentPane.add(controlPanel, BorderLayout.SOUTH);

        // --- Action Listeners ---
        startButton.addActionListener(e -> runSimulation());
        cancelButton.addActionListener(e -> {
            if (worker != null && !worker.isDone()) {
                logArea.append("\n>>> CANCELLATION REQUESTED <<<\n");
                worker.cancel(true);
            }
        });
    }
    
    private JTextField addField(JPanel panel, GridBagConstraints gbc, String labelText, int yPos, String defaultValue) {
        gbc.gridx = 0;
        gbc.gridy = yPos;
        panel.add(new JLabel(labelText), gbc);
        
        gbc.gridx = 1;
        JTextField textField = new JTextField(10);
        textField.setText(defaultValue);
        panel.add(textField, gbc);
        return textField;
    }

    
    
    private void runSimulation() {
        startButton.setEnabled(false);
        cancelButton.setEnabled(true);
        logArea.setText("");

        worker = new SwingWorker<>() {
            @Override
            protected Void doInBackground() throws Exception {
                Consumer<String> logConsumer = this::publish;
                
                String projectRoot = System.getProperty("user.dir");
                
                SimRun.Configuration config = new SimRun.Configuration(
                    Double.parseDouble(nAnaField.getText()),
                    Double.parseDouble(initialSearchField.getText()), 0.025, 0.005, 15, "4",
                    projectRoot + File.separator + "model" + File.separator + "NN_NewComsol.mph",
                    projectRoot + File.separator + "output" + File.separator + "images",
                    projectRoot + File.separator + "output" + File.separator + "results.csv"
                );

                double startWl = Double.parseDouble(startWlField.getText());
                double endWl = Double.parseDouble(endWlField.getText());
                double stepWl = Double.parseDouble(stepWlField.getText());
                
                SimRun.runSweep(config, logConsumer, startWl, endWl, stepWl);
                return null;
            }

            @Override
            protected void process(java.util.List<String> chunks) {
                for (String line : chunks) {
                    logArea.append(line + "\n");
                }
            }

            @Override
            protected void done() {
                try {
                    get(); 
                    if (isCancelled()) {
                        JOptionPane.showMessageDialog(SimGUI.this, "The run was cancelled by the user.", "Run Cancelled", JOptionPane.WARNING_MESSAGE);
                    } else {
                        JOptionPane.showMessageDialog(SimGUI.this, "Wavelength sweep complete!", "Finished", JOptionPane.INFORMATION_MESSAGE);
                    }
                } catch (Exception e) {
                    if (e instanceof java.util.concurrent.CancellationException) {
                         JOptionPane.showMessageDialog(SimGUI.this, "The run was cancelled by the user.", "Run Cancelled", JOptionPane.WARNING_MESSAGE);
                    } else {
                        JOptionPane.showMessageDialog(SimGUI.this, "An error occurred during the run:\n" + e.getMessage(), "Error", JOptionPane.ERROR_MESSAGE);
                    }
                } finally {
                    startButton.setEnabled(true);
                    cancelButton.setEnabled(false);
                }
            }
        };
        worker.execute();
    }

    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> new SimGUI().setVisible(true));
    }
    
}