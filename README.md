# 🗺️ CartoAgent - Map Style Transfer and Evaluation

Welcome to the official repository for our work **"CartoAgent: a multimodal large language model-powered multi-agent cartographic framework for map style transfer and evaluation"**!

## 🌟 Overview

The rapid development of generative artificial intelligence (GenAI) presents new opportunities to advance the cartographic process. Previous studies have either overlooked the artistic aspects of maps or faced challenges in creating both accurate and informative maps. In this study, we propose a novel multi-agent cartographic framework, CartoAgent, powered by multimodal large language models (MLLMs). Our framework simulates the three stages of the cartographic process: preparation, map design, and evaluation. At each stage, different MLLMs act as agents with distinct roles, collaborating, discussing, and utilizing tools to automatically create maps. By leveraging visual aesthetic capabilities of MLLMs and their world knowledge, CartoAgent generates maps that are both visually appealing and informative. In particular, by separating style from geographic data, our agents focus solely on designing stylesheets without modifying the vector-based data, thereby ensuring geographic accuracy. We applied this framework to a specific task centered on map restyling—namely, map style transfer and evaluation. Through extensive experiments and a human evaluation study, we confirm that the results align with human perceptions and demonstrate the effectiveness of our framework. CartoAgent can be extended to support a variety of cartographic design decisions, informing future integrations of GenAI in cartography.

![Overview](./assets/Overview.jpg)

## 📁 Repository Structure

This repo provides the official Python implementation of CartoAgent, along with teaching materials developed for the Cartography & Maps course at UT Austin. For detailed instructions on how to use the code, please refer to the [README](./research/README.md) file.

| Path                                        | Description                |
| ------------------------------------------- | -------------------------- |
| ./research                                  | Source code for CartoAgent |
| ./teaching                                  | Teaching materials         |
| ./teaching/Spring25-Lab7-GRG356-CartoAI.pdf | Lecture slides             |
| ./teaching/Lab7PromptTutorial.docx          | Prompt design tutorial     |
| ./teaching/Lab7Data                         | Dataset                    |

## 🚀 Future Directions

We aim to extend CartoAgent in several directions:

- 🌐 Support for diverse platforms (e.g., QGIS, Google Maps);
- 🧠 Integration with image generation models (e.g., DALL·E) for generative icons.

## 📫 Contact

For questions, feedback, or collaboration inquiries, feel free to:

- Open an Issue;
- Or reach out to the maintainers directly at: chenglongw@stu.pku.edu.cn; yuhao.kang@austin.utexas.edu
