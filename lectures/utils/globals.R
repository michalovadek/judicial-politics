#### globals ####

# library -----------------------------------------------------------------

suppressWarnings(
  library(tidyverse)
)

# seed
set.seed(953109)

# custom ggplot theme -----------------------------------------------------

# Create a custom theme
theme_minimalist <- function() {
  theme_minimal() +
    theme(
      axis.line = element_line(color = "black"),
      axis.line.x = element_line(color = "black", linewidth = 0.5, arrow = arrow(length = unit(0.2, "cm"))),
      axis.line.y = element_line(color = "black", linewidth = 0.5, arrow = arrow(length = unit(0.2, "cm"))),
      axis.ticks = element_blank(),
      panel.border = element_blank(),
      panel.background = element_blank(),
      panel.grid = element_blank(),
      plot.title = element_text(hjust = 0.5, size = 14, face = "bold"),
      plot.caption = element_text(size = 8, hjust = 0.5),
      legend.position = "none"
    ) +
    labs(x = NULL , y = NULL)
}
