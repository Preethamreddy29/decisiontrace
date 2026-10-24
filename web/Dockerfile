FROM node:22-alpine

WORKDIR /workspace
RUN chown node:node /workspace
USER node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
